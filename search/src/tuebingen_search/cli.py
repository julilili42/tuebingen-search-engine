"""Command line interface: index building, interactive search, batch runs."""

from __future__ import annotations

import argparse
import logging

from .batch import batch
from .indexer import index
from .search import SearchEngine

HIGHLIGHT_START = "\033[1;33m"
HIGHLIGHT_END = "\033[0m"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tuebingen-search",
        description="Search engine for English web content about Tübingen",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="build the index from a crawl")
    index_parser.add_argument("-d", "--dir", default="data/crawl",
                              help="crawl directory (with pages.jsonl)")
    index_parser.add_argument("-o", "--output", default="index.bin")

    search_parser = subparsers.add_parser("search", help="run a single query")
    search_parser.add_argument("-i", "--index", default="index.bin")
    search_parser.add_argument("-q", "--query", required=True)
    search_parser.add_argument("-t", "--top-n", type=int, default=10)
    search_parser.add_argument("--no-rm3", action="store_true",
                               help="disable pseudo-relevance feedback")
    search_parser.add_argument("--no-semantic", action="store_true",
                               help="disable LSA semantic re-ranking")
    search_parser.add_argument("--no-proximity", action="store_true",
                               help="disable term-proximity re-ranking")

    batch_parser = subparsers.add_parser(
        "batch", help="run a tab-separated query file, write a results file"
    )
    batch_parser.add_argument("-i", "--index", default="index.bin")
    batch_parser.add_argument("-q", "--queries", required=True,
                              help="file with '<number>\\t<query>' per line")
    batch_parser.add_argument("-o", "--output", default="results.txt")

    return parser


def _print_results(engine: SearchEngine, args: argparse.Namespace) -> None:
    response = engine.retrieve(
        args.query,
        top_n=args.top_n,
        use_rm3=not args.no_rm3,
        use_semantic=not args.no_semantic,
        use_proximity=not args.no_proximity,
    )

    if not response.results:
        print("No results.")
        return

    for result in response.results:
        snippet = _highlight(result.snippet, result.highlights)
        print(
            f"\n{result.rank:>3}. {result.title}\n"
            f"     {result.url}\n"
            f"     score {result.score:.4f}"
            f" (bm25 {result.bm25_score:.4f}, semantic {result.semantic_score:.4f},"
            f" proximity {result.proximity_score:.4f})\n"
            f"     {snippet}"
        )

    if response.expansion_terms:
        print(f"\nQuery was expanded with: {', '.join(response.expansion_terms)}")
    print(f"{response.total_matches} documents matched.")


def _highlight(snippet: str, highlights: list[tuple[int, int]]) -> str:
    for start, end in sorted(highlights, reverse=True):
        snippet = (
            snippet[:start]
            + HIGHLIGHT_START + snippet[start:end] + HIGHLIGHT_END
            + snippet[end:]
        )
    return snippet


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args()

    if args.command == "index":
        index(args.dir, args.output)
    elif args.command == "search":
        _print_results(SearchEngine(args.index), args)
    elif args.command == "batch":
        batch(SearchEngine(args.index), args.queries, args.output)


if __name__ == "__main__":
    main()
