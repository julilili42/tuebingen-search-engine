"""Search over a serialized index."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import msgpack

from .tokenizer import tokenize


@dataclass(frozen=True)
class SearchResult:
    rank: int
    score: float
    path: str
    snippet: str


def search(index_path: str, query: str, top_n: int) -> list[SearchResult]:
    start = time.perf_counter()

    with Path(index_path).open("rb") as index_file:
        print(f"INFO: Opened file after {_elapsed(start)}", flush=True)
        load_start = time.perf_counter()
        print(f"INFO: Reading {index_path} inverted index.", flush=True)
        search_index = msgpack.unpack(index_file, raw=False)

    print(f"INFO: Loaded index after {_elapsed(load_start)}", flush=True)
    documents = search_index["documents"]
    inverted_index = search_index["inverted_index"]
    print(
        f"INFO: {index_path} contains {len(documents)} documents.",
        flush=True,
    )

    search_start = time.perf_counter()
    query_terms = sorted(set(tokenize(query)))

    if not query_terms:
        print("ERROR: No searchable query terms in query.", flush=True)
        return []

    print(f"INFO: Searching for {' '.join(query_terms)!r} ...", flush=True)

    scores: dict[int, float] = {}
    for term in query_terms:
        for doc_index, score in inverted_index.get(term, []):
            scores[doc_index] = scores.get(doc_index, 0.0) + score

    ranked_results = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    search_results: list[SearchResult] = []

    for rank, (doc_index, score) in enumerate(ranked_results[:top_n], start=1):
        path, length, snippet = documents[doc_index]
        result = SearchResult(
            rank=rank,
            score=score,
            path=path,
            snippet=snippet,
        )
        search_results.append(result)
        print(
            f"\n{rank:>2}. score: {score:>8.3f}\n"
            f"            path:    {path}\n"
            f"            length:  {length} terms\n"
            f"            snippet: {snippet}",
            flush=True,
        )

    print(f"INFO: Search computation took {_elapsed(search_start)}", flush=True)
    return search_results


def _elapsed(start: float) -> str:
    return f"{time.perf_counter() - start:.6f}s"
