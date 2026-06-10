from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from .urls import url_slug
import httpx
from http import HTTPStatus

logger = logging.getLogger(__name__)

def fetch_bytes(
    client: httpx.Client,
    url: str,
    retry_delay: float,
    retries: int,
) -> bytes:
    for attempt in range(retries):
        if attempt > 0:
            logger.info("Retry attempt %d ...", attempt)

        try:
            response = client.get(url)
            status = response.status_code

            if status == HTTPStatus.TOO_MANY_REQUESTS:
                # extract retry after field from header to get exact delay time
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        # extraction was not successfull, use delay probing...
                        delay = min((attempt + 1) * retry_delay, 30.0)
                else:
                    delay = min((attempt + 1) * retry_delay, 30.0)

                logger.warning("Rate limited. Waiting %ss", delay)
                time.sleep(delay)
                continue

            if status < 200 or status >= 300:
                logger.warning("Bad status %d for %s", status, url)
                continue

            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                logger.info("Skipping non-html file %s", url)
                continue
        
            return response.content

        except httpx.RequestError as exc:
            logger.warning("Failed to fetch %s with error %s", url, exc)
            delay = min((attempt + 1) * retry_delay, 30.0)
            time.sleep(delay)
            continue

    raise RuntimeError(f"ERROR: Failed to fetch {url} after {retries} retries")


def save_html(hostname: str, base_dir: str, page_url: str, body: bytes) -> str:
    digest = hashlib.sha256(page_url.encode("utf-8")).hexdigest()[:8]
    file_name = f"{digest}-{url_slug(page_url)}.html"

    directory = Path(base_dir) / hostname
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / file_name
    path.write_bytes(body)
    return str(path)
