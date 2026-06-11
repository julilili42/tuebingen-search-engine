"""Topical focus: keep the crawl close to English content about Tübingen."""

from __future__ import annotations

import re

TUEBINGEN_PATTERN = re.compile(r"t(?:ü|ue?)bingen", re.IGNORECASE)

# Regions/places tightly associated with Tübingen; weaker evidence than a
# direct mention but enough to keep neighbourhood pages crawlable.
NEARBY_TERMS = re.compile(
    r"neckar|hohent|bebenhausen|schwaben|swabia|baden-w(?:ü|ue?)rttemberg",
    re.IGNORECASE,
)


def mentions_tuebingen(text: str) -> int:
    return len(TUEBINGEN_PATTERN.findall(text))


def is_page_relevant(url: str, title: str, text: str) -> bool:
    """A page is stored only if it is clearly about Tübingen."""
    if TUEBINGEN_PATTERN.search(url) or TUEBINGEN_PATTERN.search(title):
        return True
    return mentions_tuebingen(text) >= 3


def url_priority(url: str, source_relevant: bool, seed_hosts: frozenset[str], host: str) -> float:
    """Frontier priority for an outgoing link; higher is crawled earlier."""
    priority = 0.0

    if TUEBINGEN_PATTERN.search(url):
        priority += 3.0
    if NEARBY_TERMS.search(url):
        priority += 0.5
    if host in seed_hosts:
        priority += 2.0
    if source_relevant:
        priority += 1.0
    if "/en" in url or "lang=en" in url or host.startswith("en."):
        priority += 1.0

    # Prefer shallow pages: hubs link to most of the relevant content.
    depth = url.count("/") - 2
    priority -= 0.2 * max(depth, 0)

    return priority
