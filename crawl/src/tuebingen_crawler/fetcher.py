from __future__ import annotations

import hashlib
import logging
import time
from http import HTTPStatus
from pathlib import Path

import httpx

from .urls import url_slug

logger = logging.getLogger(__name__)

RETRYABLE_STATUSES = {
    HTTPStatus.TOO_MANY_REQUESTS,
    HTTPStatus.INTERNAL_SERVER_ERROR,
    HTTPStatus.BAD_GATEWAY,
    HTTPStatus.SERVICE_UNAVAILABLE,
    HTTPStatus.GATEWAY_TIMEOUT,
}


class FetchError(Exception):
    pass


def fetch_html(
    client: httpx.Client,
    url: str,
    retries: int,
    retry_delay: float,
    max_content_bytes: int,
) -> tuple[bytes, str]:
    """Fetch a URL and return (body, final_url_after_redirects).

    Retries transient failures with linear backoff; permanent failures
    (4xx other than 429, non-HTML content) abort immediately.
    """
    for attempt in range(retries):
        if attempt > 0:
            time.sleep(min(attempt * retry_delay, 30.0))
            logger.info("Retry %d for %s", attempt, url)

        try:
            response = client.get(url)
        except httpx.HTTPError as exc:
            logger.warning("Request error for %s: %s", url, exc)
            continue

        status = response.status_code
        if status in RETRYABLE_STATUSES:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    time.sleep(min(float(retry_after), 30.0))
                except ValueError:
                    pass
            continue

        if status < 200 or status >= 300:
            raise FetchError(f"status {status} for {url}")

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            raise FetchError(f"non-html content type {content_type!r} for {url}")

        if len(response.content) > max_content_bytes:
            raise FetchError(f"content too large ({len(response.content)} bytes) for {url}")

        return response.content, str(response.url)

    raise FetchError(f"failed to fetch {url} after {retries} attempts")


def save_html(save_dir: str, host: str, page_url: str, body: bytes) -> str:
    digest = hashlib.sha256(page_url.encode("utf-8")).hexdigest()[:8]
    directory = Path(save_dir) / host
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / f"{digest}-{url_slug(page_url)}.html"
    path.write_bytes(body)
    return str(path)
