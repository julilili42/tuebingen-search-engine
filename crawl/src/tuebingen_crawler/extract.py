from __future__ import annotations

from dataclasses import dataclass, field

from selectolax.lexbor import LexborHTMLParser

REMOVED_TAGS = ["script", "style", "noscript", "template"]

@dataclass
class ParsedPage:
    title: str
    lang: str | None
    text: str
    links: list[tuple[str, str]] = field(default_factory=list)  


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def parse_page(body: bytes) -> ParsedPage:
    tree = LexborHTMLParser(body)

    # collect <html lang="...">
    html_node = tree.css_first("html")
    lang = html_node.attributes.get("lang") if html_node is not None else None

    # collect title
    title_node = tree.css_first("title")
    title = _normalize_text(title_node.text(strip=True)) if title_node else ""

    # collect links
    links: list[tuple[str, str]] = []
    for a in tree.css("a"):
        href = a.attributes.get("href")
        if href:
            links.append((href, _normalize_text(a.text(deep=True, strip=True))))

    tree.strip_tags(REMOVED_TAGS, recursive=True)
    body_node = tree.body
    text = (
        _normalize_text(body_node.text(deep=True, separator=" ", strip=True))
        if body_node is not None
        else ""
    )

    return ParsedPage(title=title, lang=lang, text=text, links=links)
