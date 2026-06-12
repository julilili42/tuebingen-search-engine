from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict, List
from .models import Statistics, CrawlState, Config, CrawlSite
from .storage import save_state, load_state, generate_state_path
from .urls import canonical_url, extract_urls, hostname_for_url
from .fetcher import fetch_bytes, save_html
from urllib.parse import urlparse
import httpx
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)

# before we crawl a url we have to load the `robots.txt` file
def load_robots(client: httpx.Client, site: CrawlSite) -> RobotFileParser:
    parsed = urlparse(site.url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid site URL: {site.url}")
    
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        response = client.get(robots_url, timeout=5.0, follow_redirects=True)
        if response.status_code == 404:
                parser.parse([])
                return parser

        response.raise_for_status()
        parser.parse(response.text.splitlines())
        return parser

    except httpx.RequestError as exc:
        logger.warning("Could not fetch robots.txt for %s: %s", site.url, exc)
        parser.parse([])
        return parser

def crawl_hostname(config: Config) -> Dict[str, Dict[str, str]]:
    index: Dict[str, Dict[str, str]] = {}
    headers = {"Accept": config.accept, "User-Agent": config.user_agent}

    for site in config.sites:
        with httpx.Client(timeout=site.request_timeout, headers=headers) as client:            
            robot_parser = load_robots(client, site)

            # skips urls which categorically disallow crawling
            if not robot_parser.can_fetch(config.user_agent, site.url):
                logger.warning("Skipping %s because robots.txt disallows it", site.url)
                continue

            seen_urls: Dict[str, bool] = {}
            statistics = Statistics()
            site_index = crawl_site(client, site, seen_urls, config.save_dir, config.save_state_every, statistics, robot_parser, config.user_agent)
            index[site.url] = site_index 

            statistics.print()
            statistics.reset()

    return index

def crawl_site(
    client: httpx.Client,
    site: CrawlSite,
    seen_urls: Dict[str, bool],
    save_dir: Path, 
    save_state_every: int,
    statistics: Statistics,
    robot_parser: RobotFileParser,
    user_agent: str
) -> Dict[str, str]:
    starting_url = site.url

    # restricts crawler to stay on hostname it started on
    allowed_host = hostname_for_url(starting_url)
    # normalize starting url
    canonical_start, is_canonical = canonical_url(starting_url, starting_url, allowed_host)
    if not is_canonical:
        raise ValueError(f"ERROR: starting url {starting_url} is not canonical")



    state_path = generate_state_path(save_dir, allowed_host, canonical_start)
    state, loaded = load_state(state_path)

    if loaded:
        queue = state.queue
        head = state.head
        seen_urls = state.seen
        site_index = state.index
        statistics.fetched = state.statistics.fetched
        statistics.discovered = state.statistics.discovered
        statistics.failed = state.statistics.failed
        statistics.saved = state.statistics.saved

        if head < len(queue):
            logger.info("Resuming crawl at %s", queue[head])
        else:
            logger.info("Crawl state is already complete")
    else:
        queue = [canonical_start]
        head = 0
        seen_urls[canonical_start] = True
        site_index: Dict[str, str] = {}




    while head < len(queue):
        if site.max_pages >= 0 and len(site_index) >= site.max_pages:
            break

        current_url = queue[head]
        head += 1
        statistics.inc_discovered()

        if not robot_parser.can_fetch(user_agent, current_url):
            logger.info("Skipping disallowed URL: %s", current_url)
            statistics.inc_failed()
            continue

        logger.info("Fetching bytes from %s", current_url)
        try:
            body = fetch_bytes(
                client=client,
                url=current_url,
                retry_delay=site.retry_delay,
                retries=site.retries,
            )
        except Exception as exc:
            logger.error("Failed to fetch %s with error %s", current_url, exc)
            statistics.inc_failed()
            continue

        statistics.inc_fetched()
        time.sleep(site.request_delay)

        try:
            path = save_html(allowed_host, save_dir, current_url, body)
        except Exception as exc:
            logger.error("Failed to save html %s with error %s", current_url, exc)
            statistics.inc_failed()
            continue

        site_index[current_url] = path
        statistics.inc_saved()

        try:
            extracted_urls = extract_urls(seen_urls, body, current_url, allowed_host)
        except Exception as exc:
            logger.error("Failed to extract urls at %s with error %s", current_url, exc)
            statistics.inc_failed()
            continue

        queue.extend(extracted_urls)
        maybe_save_progress(save_state_every, state_path, queue, head, seen_urls, site_index, statistics)

    save_progress(state_path, queue, head, seen_urls, site_index, statistics)
    return site_index

def save_progress(
    state_path: str,
    queue: List[str], 
    head: int, 
    seen_urls: Dict[str, bool],
    site_index: Dict[str, str],
    statistics: Statistics,
) -> None:
    save_state(
        state_path,
        CrawlState(
            queue=queue,
            head=head,
            seen=seen_urls,
            index=site_index,
            statistics=statistics,
        ),
    )

def maybe_save_progress(
    save_state_every: int,
    state_path: str,
    queue: List[str], 
    head: int, 
    seen_urls: Dict[str, bool],
    site_index: Dict[str, str],
    statistics: Statistics,
) -> None:
    if save_state_every <= 0:
        return

    if head % save_state_every == 0:
        save_progress(state_path, queue, head, seen_urls, site_index, statistics)




# saves page summary of all crawled pages
def save_jsonl(path: str | Path, index: Dict[str, Dict[str, str]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for site_url, site_index in index.items():
            for url, file_path in site_index.items():
                row = {
                    "site": site_url,
                    "url": url,
                    "path": file_path,
                }
                file.write(json.dumps(row, ensure_ascii=False) + "\n")


