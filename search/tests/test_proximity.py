import pytest

from tuebingen_search.search import SearchEngine
from tuebingen_search.tokenizer import stem


@pytest.fixture(scope="session")
def engine(index_path) -> SearchEngine:
    return SearchEngine(index_path)


def query_stems(*words: str) -> frozenset[str]:
    return frozenset(stem(word) for word in words)


def test_adjacent_terms_score_one(engine):
    # Document 4 ("Weekly market") contains "weekly market" adjacent in title.
    assert engine._proximity(4, query_stems("weekly", "market")) == 1.0


def test_distant_terms_score_below_adjacent(engine):
    # Document 7 mentions castle and punting with words in between.
    distant = engine._proximity(7, query_stems("castle", "punting"))
    assert 0.0 < distant < 1.0


def test_missing_term_scores_zero(engine):
    # Document 0 (castle) never mentions punting.
    assert engine._proximity(0, query_stems("castle", "punting")) == 0.0


def test_single_term_queries_skip_proximity(engine):
    response = engine.retrieve("castle")
    assert all(result.proximity_score == 0.0 for result in response.results)


def test_multi_term_queries_populate_proximity(engine):
    response = engine.retrieve("weekly market", use_rm3=False)
    top = response.results[0]
    assert top.url == "https://site-b.test/market"
    assert top.proximity_score == 1.0


def test_proximity_can_be_disabled(engine):
    response = engine.retrieve("weekly market", use_proximity=False)
    assert all(result.proximity_score == 0.0 for result in response.results)
