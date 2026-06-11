from __future__ import annotations

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)


class RobotsCache:
    """Fetches and caches robots.txt per host.

    An unreachable or missing robots.txt is treated as allow-all, which is the
    conventional interpretation for 404 responses.
    """

    def __init__(self, client: httpx.Client, user_agent: str) -> None:
        self._client = client
        self._user_agent = user_agent
        self._parsers: dict[str, RobotFileParser | None] = {}

    def _parser_for(self, url: str) -> RobotFileParser | None:
        parsed = urlparse(url)
        host_key = f"{parsed.scheme}://{parsed.netloc}"

        if host_key not in self._parsers:
            self._parsers[host_key] = self._fetch(host_key)
        return self._parsers[host_key]

    def _fetch(self, host_key: str) -> RobotFileParser | None:
        robots_url = f"{host_key}/robots.txt"
        try:
            response = self._client.get(robots_url)
        except httpx.HTTPError as exc:
            logger.info("robots.txt unreachable for %s (%s); allowing all", host_key, exc)
            return None

        if response.status_code >= 400:
            return None

        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser

    def allowed(self, url: str) -> bool:
        parser = self._parser_for(url)
        return parser is None or parser.can_fetch(self._user_agent, url)

    def crawl_delay(self, url: str) -> float | None:
        parser = self._parser_for(url)
        if parser is None:
            return None
        delay = parser.crawl_delay(self._user_agent)
        return float(delay) if delay is not None else None
