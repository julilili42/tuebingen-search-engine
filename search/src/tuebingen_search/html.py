"""HTML extraction helpers."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

# Content-bearing tags; restricting extraction to these acts as a simple
# boilerplate filter (navigation, footers and menus are mostly skipped).
SELECTED_TAGS = {
    "h1", "h2", "h3", "h4", "p", "li", "td", "th", "figcaption", "blockquote",
}

# Boilerplate containers are skipped entirely, including any nested
# content tags (navigation menus are usually <nav><ul><li>...).
SKIPPED_TAGS = {
    "script", "style", "noscript", "template",
    "nav", "header", "footer", "aside", "form", "button",
}


@dataclass(frozen=True)
class ExtractedPage:
    title: str
    text: str


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._selected_depth = 0
        self._skip_depth = 0
        self._in_title = False
        self._chunks: list[str] = []
        self._title_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        elif tag in SKIPPED_TAGS:
            self._skip_depth += 1
        elif tag in SELECTED_TAGS:
            self._selected_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        elif tag in SKIPPED_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in SELECTED_TAGS and self._selected_depth > 0:
            self._selected_depth -= 1
            self._chunks.append(" ")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        clean_text = " ".join(data.split())
        if not clean_text:
            return
        if self._in_title:
            self._title_chunks.append(clean_text)
        elif self._selected_depth > 0:
            self._chunks.append(clean_text)
            self._chunks.append(" ")

    def extracted(self) -> ExtractedPage:
        return ExtractedPage(
            title=" ".join(self._title_chunks),
            text="".join(self._chunks).strip(),
        )


def is_html_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".html"


def extract_page(file_path: Path) -> ExtractedPage:
    parser = TextExtractor()
    parser.feed(file_path.read_text(encoding="utf-8", errors="replace"))
    return parser.extracted()
