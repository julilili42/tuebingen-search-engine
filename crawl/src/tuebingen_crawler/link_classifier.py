from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import unquote, urlparse

from .models import REL_THRESHOLD
from .semantic import topic_similarity
from .tuebingen_terms import has_tuebingen
from .urls import normalize_host

@dataclass(frozen=True)
class FrontierConfig:
    threshold: float = 4.0
    max_depth: int = 5

    def within_depth(self, depth: int) -> bool:
        return depth <= self.max_depth

    def should_enqueue(self, score: float, depth: int) -> bool:
        return score >= self.threshold and self.within_depth(depth)

@dataclass(frozen=True)
class ParentRelevanceConfig:
    # continuous inheritance of the parent page's relevance
    weight: float = 1.0
    # cap on parent_relevance so one very strong page cannot dominate
    cap: float = 4.0
    # inherited pull fades with crawl depth
    depth_decay: float = 0.85

@dataclass(frozen=True)
class SemanticScoringConfig:
    # anchors are short/noisy, so only strong matches from strong parents lift links
    admit_threshold: float = 0.7
    min_parent_relevance: float = REL_THRESHOLD * 2.0

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
    # archive mirrors are skipped to avoid duplicates
    blocked_hosts: frozenset[str] = frozenset({
        "web.archive.org",
        "archive.today",
        "archive.is",
        "archive.ph",
    })
    # explicit lexical/structural cue weights (experimentally chosen)
    feature_weights: dict[str, float] = field(default_factory=lambda: {
        "anchor_has_tuebingen": 4.0,
        "url_has_tuebingen": 3.0,
        "internal_link": 1.0,
        "semantic_relevance": 3.0,
    })
    parent_relevance: ParentRelevanceConfig = field(default_factory=ParentRelevanceConfig)
    semantic: SemanticScoringConfig = field(default_factory=SemanticScoringConfig)

FRONTIER_CONFIG = FrontierConfig()
LINK_CONFIG = LinkScoringConfig()

@dataclass(frozen=True)
class LinkVerdict:
    url: str
    score: float
    depth: int

    @property
    def enqueue(self) -> bool:
        return FRONTIER_CONFIG.should_enqueue(self.score, self.depth)

def _host(url: str) -> str:
    try:
        netloc = urlparse(url).hostname or ""
    except ValueError:
        return ""
    return normalize_host(netloc)

def _is_skipable(url: str) -> bool:
    if _host(url) in LINK_CONFIG.blocked_hosts:
        return True
    if url.lower().endswith(LINK_CONFIG.resource_suffixes):
        return True
    path = urlparse(url).path.lower()
    return any(kw in path for kw in LINK_CONFIG.skip_path_words)

def _url_path_text(url: str) -> str:
    try:
        path = unquote(urlparse(url).path)
    except ValueError:
        return ""

    return " ".join(part for part in re.split(r"[/_.-]+", path) if part)

def _link_text(anchor: str, url: str) -> str:
    return " ".join(part for part in (anchor.strip(), _url_path_text(url)) if part)

def semantic_link_score(anchor: str, url: str) -> float:
    text = _link_text(anchor, url)
    if not text:
        return 0.0

    sim = topic_similarity("", text)
    threshold = LINK_CONFIG.semantic.admit_threshold
    if sim < threshold:
        return 0.0

    return (sim - threshold) / (1.0 - threshold)

def _should_score_semantically(score: float, parent_relevance: float, depth: int) -> bool:
    return (
        score < FRONTIER_CONFIG.threshold
        and FRONTIER_CONFIG.within_depth(depth)
        and parent_relevance >= LINK_CONFIG.semantic.min_parent_relevance
    )

def link_score(
    anchor: str,
    url: str,
    parent_relevance: float,
    parent_host: str,
    depth: int = 0,
) -> float:
    if _is_skipable(url):
        return 0.0

    weights = LINK_CONFIG.feature_weights
    score = 0.0
    if has_tuebingen(anchor):
        score += weights["anchor_has_tuebingen"]
    if has_tuebingen(url):
        score += weights["url_has_tuebingen"]
    if _host(url) == normalize_host(parent_host):
        score += weights["internal_link"]

    # depth decayed inheritance of the parents relevance
    parent = LINK_CONFIG.parent_relevance
    rel_norm = min(parent_relevance / REL_THRESHOLD, parent.cap)
    score += parent.weight * rel_norm * (parent.depth_decay ** depth)

    if _should_score_semantically(score, parent_relevance, depth):
        score += weights["semantic_relevance"] * semantic_link_score(anchor, url)

    return score

def classify_link(
    anchor: str,
    url: str,
    parent_relevance: float,
    parent_host: str,
    depth: int,
) -> LinkVerdict:
    score = link_score(anchor, url, parent_relevance, parent_host, depth)
    return LinkVerdict(url=url, score=score, depth=depth)
