from dataclasses import dataclass
from pathlib import Path

TermFrequency = dict[str, int]

@dataclass(frozen=True)
class Posting:
    doc_index: int
    score: float


@dataclass(frozen=True)
class Document:
    path: Path
    url: str | None
    length: int
    text_snippet: str


@dataclass(frozen=True)
class SearchIndex:
    documents: list[Document]
    inverted_index: dict[str, list[Posting]]


@dataclass(frozen=True)
class SearchResult:
    rank: int
    score: float
    path: Path
    url: str | None
    snippet: str

