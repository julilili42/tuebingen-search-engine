from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

SKIPPED_TEXT_TAGS = {
    "script", "style", "noscript", "template", "svg",
    "nav", "header", "footer", "aside", "form", "button",
}


@dataclass
class ParsedPage:
    links: list[str] = field(default_factory=list)
    title: str = ""
    description: str = ""
    lang: str = ""
    text: str = ""


class PageParser(HTMLParser):
    """Single-pass extraction of links, title, meta description, lang and text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._links: list[str] = []
        self._title_chunks: list[str] = []
        self._text_chunks: list[str] = []
        self._description = ""
        self._lang = ""
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {key.lower(): value for key, value in attrs if value is not None}

        if tag == "html" and not self._lang:
            self._lang = attributes.get("lang", "").lower()
        elif tag == "a":
            href = attributes.get("href")
            if href:
                self._links.append(href)
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = attributes.get("name", "").lower()
            if name == "description" and not self._description:
                self._description = attributes.get("content", "").strip()
        elif tag in SKIPPED_TEXT_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        elif tag in SKIPPED_TEXT_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        clean_text = " ".join(data.split())
        if not clean_text:
            return
        if self._in_title:
            self._title_chunks.append(clean_text)
        else:
            self._text_chunks.append(clean_text)

    def parsed(self) -> ParsedPage:
        return ParsedPage(
            links=self._links,
            title=" ".join(self._title_chunks),
            description=self._description,
            lang=self._lang,
            text=" ".join(self._text_chunks),
        )


def parse_page(body: bytes) -> ParsedPage:
    parser = PageParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    return parser.parsed()
