import pytest

from tuebingen_search.cli import _highlight, build_parser


def test_parser_index_defaults():
    args = build_parser().parse_args(["index"])
    assert args.dir == "data/crawl"
    assert args.output == "index.bin"


def test_parser_search_flags():
    args = build_parser().parse_args(
        ["search", "-q", "castle", "-t", "5", "--no-rm3"]
    )
    assert args.query == "castle"
    assert args.top_n == 5
    assert args.no_rm3
    assert not args.no_semantic


def test_parser_batch_requires_queries():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["batch"])

    args = build_parser().parse_args(["batch", "-q", "queries.txt", "-o", "out.txt"])
    assert args.queries == "queries.txt"
    assert args.output == "out.txt"


def test_highlight_wraps_ranges_in_ansi_codes():
    highlighted = _highlight("the castle stands", [(4, 10)])
    assert "\033[1;33mcastle\033[0m" in highlighted
    assert highlighted.startswith("the ")
