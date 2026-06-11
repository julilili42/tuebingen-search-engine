from __future__ import annotations

import logging
import time

import httpx

from .fetcher import FetchError, fetch_html, save_html
from .frontier import Frontier
from .language import is_english
from .models import CrawlConfig, CrawlState, PageRecord, Statistics
from .page import parse_page
from .relevance import is_page_relevant, url_priority
from .robots import RobotsCache
from .storage import append_page_record, load_state, save_state
from .urls import host_of, normalize_url

logger = logging.getLogger(__name__)

SEED_PRIORITY = 10.0
# Pause when every queued host is within its politeness window.
IDLE_WAIT_SECONDS = 0.2
# Safety valve: stop a crawl that fetches lots of pages but stores few.
MAX_FETCHES_PER_SAVED_PAGE = 10


def crawl(config: CrawlConfig) -> Statistics:
    """Crawl the web for English content about Tübingen.

    The crawl is resumable: state is persisted periodically and on exit (even
    on KeyboardInterrupt), and stored documents are appended to pages.jsonl
    as they are saved.
    """
    state = load_state(config.save_dir)
    if state is not None:
        frontier = Frontier.from_state(state.frontier, state.next_seq, state.seen)
        saved_urls = set(state.saved_urls)
        host_pages = dict(state.host_pages)
        statistics = state.statistics
    else:
        frontier = Frontier()
        saved_urls = set()
        host_pages = {}
        statistics = Statistics()

    seeds = [normalized for seed in config.seeds if (normalized := normalize_url(seed))]
    for seed in seeds:
        frontier.push(seed, SEED_PRIORITY)

    headers = {"Accept": config.accept, "User-Agent": config.user_agent}
    try:
        with httpx.Client(
            timeout=config.request_timeout, headers=headers, follow_redirects=True
        ) as client:
            robots = RobotsCache(client, config.user_agent)
            _crawl_loop(
                config, client, robots, frontier,
                seed_hosts=frozenset(host_of(seed) for seed in seeds),
                saved_urls=saved_urls, host_pages=host_pages, statistics=statistics,
            )
    finally:
        _persist(config.save_dir, frontier, saved_urls, host_pages, statistics)
        logger.info("Crawl stopped: %s", statistics.summary())

    return statistics


def _crawl_loop(
    config: CrawlConfig,
    client: httpx.Client,
    robots: RobotsCache,
    frontier: Frontier,
    seed_hosts: frozenset[str],
    saved_urls: set[str],
    host_pages: dict[str, int],
    statistics: Statistics,
) -> None:
    host_next_time: dict[str, float] = {}
    max_fetches = config.max_pages * MAX_FETCHES_PER_SAVED_PAGE
    pages_since_save = 0

    while frontier and len(saved_urls) < config.max_pages:
        if statistics.fetched >= max_fetches:
            logger.warning("Fetch budget exhausted (%d fetches)", statistics.fetched)
            break

        url = frontier.pop_ready(
            lambda host: time.monotonic() >= host_next_time.get(host, 0.0)
        )
        if url is None:
            time.sleep(IDLE_WAIT_SECONDS)
            continue

        host = host_of(url)
        if host_pages.get(host, 0) >= config.max_pages_per_host:
            continue

        if not robots.allowed(url):
            logger.debug("Disallowed by robots.txt: %s", url)
            statistics.skipped_robots += 1
            continue

        delay = max(
            config.host_delay,
            min(robots.crawl_delay(url) or 0.0, config.max_robots_delay),
        )
        host_next_time[host] = time.monotonic() + delay

        try:
            body, final_url = fetch_html(
                client, url, config.retries, config.retry_delay, config.max_content_bytes
            )
        except FetchError as exc:
            logger.info("Fetch failed: %s", exc)
            statistics.failed += 1
            continue
        statistics.fetched += 1

        page_url = normalize_url(final_url) or url
        if page_url != url:
            frontier.seen.add(page_url)
        if page_url in saved_urls:
            continue

        page = parse_page(body)
        relevant = is_page_relevant(page_url, page.title, page.text)
        if not relevant:
            statistics.skipped_relevance += 1
        elif not is_english(page.text, page.lang):
            statistics.skipped_language += 1
        else:
            path = save_html(config.save_dir, host_of(page_url), page_url, body)
            append_page_record(
                config.save_dir,
                PageRecord(
                    url=page_url,
                    path=path,
                    title=page.title,
                    description=page.description,
                ),
            )
            saved_urls.add(page_url)
            host_pages[host] = host_pages.get(host, 0) + 1
            statistics.saved += 1
            logger.info("Saved %d/%d: %s", len(saved_urls), config.max_pages, page_url)

        # Off-topic pages are dead ends; expanding them would drift away from
        # Tübingen. Relevant pages are expanded even if non-English, since
        # they often link to their English versions.
        if relevant:
            _push_links(frontier, page.links, page_url, seed_hosts)

        pages_since_save += 1
        if pages_since_save >= config.save_state_every:
            _persist(config.save_dir, frontier, saved_urls, host_pages, statistics)
            pages_since_save = 0


def _push_links(
    frontier: Frontier,
    links: list[str],
    base_url: str,
    seed_hosts: frozenset[str],
) -> None:
    for href in links:
        normalized = normalize_url(href, base_url)
        if normalized is None:
            continue
        priority = url_priority(
            normalized, source_relevant=True, seed_hosts=seed_hosts, host=host_of(normalized)
        )
        frontier.push(normalized, priority)


def _persist(
    save_dir: str,
    frontier: Frontier,
    saved_urls: set[str],
    host_pages: dict[str, int],
    statistics: Statistics,
) -> None:
    heap, next_seq, seen = frontier.to_state()
    save_state(
        save_dir,
        CrawlState(
            frontier=heap,
            next_seq=next_seq,
            seen=seen,
            saved_urls=sorted(saved_urls),
            host_pages=host_pages,
            statistics=statistics,
        ),
    )
