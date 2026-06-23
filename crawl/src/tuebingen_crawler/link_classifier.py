from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from .models import REL_THRESHOLD
from .tuebingen_terms import has_tuebingen
from .urls import normalize_host

@dataclass(frozen=True)
class FrontierConfig:
    threshold: float = 4.0
    max_depth: int = 5

@dataclass(frozen=True)
class LinkScoringConfig:
    # sites which end in these suffixes
    resource_suffixes: tuple[str, ...] = (
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js",
        ".pdf", ".zip", ".mp4", ".mp3", ".ico", ".woff", ".woff2", ".webp"
    )
    # overview sites will be skipped
    skip_path_words: frozenset[str] = frozenset({
        "category",
        "appendix",
        "talk",
        "special:",
    })
    # weights are experimentally chosen
    feature_weights: dict[str, float] = field(default_factory=lambda: {
        "anchor_has_tuebingen": 4.0,
        "url_has_tuebingen": 3.0,
        "parent_relevant": 2.0,
        "internal_link": 1.0,
    })

FRONTIER_CONFIG = FrontierConfig()
LINK_CONFIG = LinkScoringConfig()

@dataclass(frozen=True)
class LinkVerdict:
    url: str
    score: float
    depth: int

    @property
    def enqueue(self) -> bool:
        return (
            self.score >= FRONTIER_CONFIG.threshold
            and self.depth <= FRONTIER_CONFIG.max_depth
        )


def _host(url: str) -> str:
    try:
        netloc = urlparse(url).hostname or ""
    except ValueError:
        return ""
    return normalize_host(netloc)

def _is_skipable(url: str) -> bool:
    if url.lower().endswith(LINK_CONFIG.resource_suffixes):
        return True
    path = urlparse(url).path.lower()
    return any(kw in path for kw in LINK_CONFIG.skip_path_words)

def link_score(
    anchor: str,
    url: str,
    parent_relevance: float,
    parent_host: str,
) -> float:
    if _is_skipable(url):
        return 0.0

    features = {
        "anchor_has_tuebingen": has_tuebingen(anchor),
        "url_has_tuebingen": has_tuebingen(url),
        "parent_relevant": parent_relevance >= REL_THRESHOLD,
        "internal_link": _host(url) == normalize_host(parent_host),
    }
    return sum(w for name, w in LINK_CONFIG.feature_weights.items() if features[name])

def classify_link(
    anchor: str,
    url: str,
    parent_relevance: float,
    parent_host: str,
    depth: int,
) -> LinkVerdict:
    score = link_score(anchor, url, parent_relevance, parent_host)
    return LinkVerdict(url=url, score=score, depth=depth)
