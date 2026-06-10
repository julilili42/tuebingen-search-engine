from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict
from .models import Statistics, CrawlState, Config, CrawlSite
from .storage import save_state, load_state, generate_state_path
from .urls import canonical_url, extract_urls, hostname_for_url
from .fetcher import fetch_bytes, save_html
import httpx

logger = logging.getLogger(__name__)

def crawl(config: Config) -> Dict[str, Dict[str, str]]:
    index: Dict[str, Dict[str, str]] = {}

    sites = config.sites
    save_dir = config.save_dir
    save_state_every = config.save_state_every
    headers = {"Accept": config.accept, "User-Agent": config.user_agent}

    for site in sites:
        with httpx.Client(timeout=site.request_timeout, headers=headers) as client:            
            seen_urls: Dict[str, bool] = {}
            statistics = Statistics()
            site_index = crawl_site(client, site, seen_urls, save_dir, save_state_every, statistics)
            index[site.url] = site_index 

            statistics.print()
            statistics.reset()

    return index

def crawl_site(
    client: httpx.Client,
    site: CrawlSite,
    seen_urls: Dict[str, bool],
    save_dir: str, 
    save_state_every: int,
    statistics: Statistics,
) -> Dict[str, str]:
    
    starting_url = site.url
    max_pages = site.max_pages
    retry_delay = site.retry_delay
    retries = site.retries
    request_delay = site.request_delay

    # restricts crawler to stay on hostname it started on
    allowed_host = hostname_for_url(starting_url)
    # normalize starting url
    canonical_start, is_canonical = canonical_url(starting_url, starting_url, allowed_host)
    if not is_canonical:
        raise ValueError(f"ERROR: starting url {starting_url} is not canonical")

    # generates path to save intermediate state
    state_path = generate_state_path(save_dir, allowed_host, canonical_start)

    # allows continuation of intermediate state
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
        if max_pages >= 0 and len(site_index) >= max_pages:
            break

        current_url = queue[head]
        head += 1
        statistics.inc_discovered()

        logger.info("Fetching bytes from %s", current_url)
        try:
            body = fetch_bytes(
                client=client,
                url=current_url,
                retry_delay=retry_delay,
                retries=retries,
            )
        except Exception as exc:
            logger.error("Failed to fetch %s with error %s", current_url, exc)
            statistics.inc_failed()
            continue

        statistics.inc_fetched()
        time.sleep(request_delay)

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

        if head % save_state_every == 0:
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
    return site_index

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


