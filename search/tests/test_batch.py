import pytest

from tuebingen_search.batch import batch, read_queries
from tuebingen_search.search import SearchEngine


def test_read_queries_parses_tab_separated_lines(tmp_path):
    queries_file = tmp_path / "queries.txt"
    queries_file.write_text(
        "1\ttübingen attractions\n2\tfood and drinks\n\n", encoding="utf-8"
    )
    assert read_queries(str(queries_file)) == [
        ("1", "tübingen attractions"),
        ("2", "food and drinks"),
    ]


def test_read_queries_rejects_malformed_lines(tmp_path):
    queries_file = tmp_path / "queries.txt"
    queries_file.write_text("1 no tab here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="queries.txt:1"):
        read_queries(str(queries_file))


def test_batch_writes_ranked_tsv(index_path, tmp_path):
    queries_file = tmp_path / "queries.txt"
    queries_file.write_text("1\tcastle museum\n2\tfood and drinks\n", encoding="utf-8")
    output_file = tmp_path / "results.txt"

    batch(SearchEngine(index_path), str(queries_file), str(output_file))

    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert lines

    by_query: dict[str, list[tuple[int, str, float]]] = {}
    for line in lines:
        query_number, rank, url, score = line.split("\t")
        by_query.setdefault(query_number, []).append((int(rank), url, float(score)))

    assert set(by_query) == {"1", "2"}
    for results in by_query.values():
        ranks = [rank for rank, _, _ in results]
        assert ranks == list(range(1, len(results) + 1))
        assert len(results) <= 100
        assert all(url.startswith("https://") for _, url, _ in results)
