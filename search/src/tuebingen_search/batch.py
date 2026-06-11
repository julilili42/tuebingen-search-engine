"""Batch evaluation: queries file in, ranked results file out.

Input format (tab-separated, one query per line):
    1\ttübingen attractions
Output format (tab-separated, one result per line):
    1\t1\thttps://example.com/page\t0.725
"""

from __future__ import annotations

import logging
from pathlib import Path

from .search import SearchEngine

logger = logging.getLogger(__name__)

RESULTS_PER_QUERY = 100


def read_queries(queries_path: str) -> list[tuple[str, str]]:
    queries = []
    for line_number, line in enumerate(
        Path(queries_path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = line.strip()
        if not line:
            continue
        try:
            query_number, query_text = line.split("\t", 1)
        except ValueError as exc:
            raise ValueError(
                f"{queries_path}:{line_number}: expected '<number>\\t<query>'"
            ) from exc
        queries.append((query_number.strip(), query_text.strip()))
    return queries


def batch(engine: SearchEngine, queries_path: str, output_path: str) -> None:
    """Run every query and write RESULTS_PER_QUERY ranked URLs per query."""
    queries = read_queries(queries_path)
    lines = []

    for query_number, query_text in queries:
        # Batch queries are complete; prefix completion is an instant-search
        # feature and is disabled here for deterministic evaluation runs.
        response = engine.retrieve(
            query_text, top_n=RESULTS_PER_QUERY, use_prefix=False
        )
        logger.info(
            "Query %s (%r): %d results", query_number, query_text, len(response.results)
        )
        for result in response.results:
            lines.append(
                f"{query_number}\t{result.rank}\t{result.url}\t{result.score}"
            )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Wrote %d result lines to %s", len(lines), output_path)
