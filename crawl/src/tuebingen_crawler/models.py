from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CrawlConfig:
    seeds: list[str]
    save_dir: str = "data/crawl"
    max_pages: int = 5000
    max_pages_per_host: int = 800
    request_timeout: float = 20.0
    retries: int = 3
    retry_delay: float = 5.0
    host_delay: float = 1.0
    max_robots_delay: float = 15.0
    save_state_every: int = 25
    max_content_bytes: int = 5_000_000
    accept: str = "text/html"
    user_agent: str = (
        "TuebingenSearchBot/1.0 (INFO4271 student project, University of Tuebingen)"
    )


@dataclass
class Statistics:
    fetched: int = 0
    saved: int = 0
    failed: int = 0
    skipped_robots: int = 0
    skipped_language: int = 0
    skipped_relevance: int = 0

    def summary(self) -> str:
        return (
            f"fetched={self.fetched} saved={self.saved} failed={self.failed} "
            f"robots={self.skipped_robots} non-english={self.skipped_language} "
            f"off-topic={self.skipped_relevance}"
        )


@dataclass(frozen=True)
class PageRecord:
    """One stored document; serialized as a line of pages.jsonl."""

    url: str
    path: str
    title: str
    description: str


@dataclass
class CrawlState:
    """Everything needed to resume an interrupted crawl."""

    frontier: list[list] = field(default_factory=list)  # [priority, seq, url]
    next_seq: int = 0
    seen: list[str] = field(default_factory=list)
    saved_urls: list[str] = field(default_factory=list)
    host_pages: dict[str, int] = field(default_factory=dict)
    statistics: Statistics = field(default_factory=Statistics)
