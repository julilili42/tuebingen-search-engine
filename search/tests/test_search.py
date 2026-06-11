import pytest

from tuebingen_search.search import SearchEngine
from tuebingen_search.tokenizer import stem


@pytest.fixture(scope="session")
def engine(index_path) -> SearchEngine:
    return SearchEngine(index_path)


def test_bm25_ranks_castle_pages_first(engine):
    response = engine.retrieve(
        "castle", use_rm3=False, use_semantic=False, use_mmr=False
    )
    urls = [result.url for result in response.results]

    assert set(urls[:2]) == {
        "https://site-a.test/castle",
        "https://site-a.test/castle-garden",
    }
    assert "https://site-c.test/attractions" in urls


def test_pure_bm25_scores_are_descending_and_normalized(engine):
    response = engine.retrieve(
        "castle museum", use_rm3=False, use_semantic=False, use_mmr=False
    )
    scores = [result.score for result in response.results]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == 1.0


def test_full_pipeline_keeps_castle_pages_on_top(engine):
    response = engine.retrieve("castle museum")
    assert response.results[0].url in {
        "https://site-a.test/castle",
        "https://site-a.test/castle-garden",
    }


def test_rm3_expands_the_query_with_surface_forms(engine):
    response = engine.retrieve("castle")
    assert response.expansion_terms
    # Expansion terms are display-friendly words, not stems of the query.
    assert all(stem(term) != stem("castle") for term in response.expansion_terms)
    assert all(term == term.lower() and term.isalpha() for term in response.expansion_terms)


def test_semantic_scores_populated(engine):
    assert engine.semantic_enabled
    response = engine.retrieve("castle")
    assert any(result.semantic_score > 0 for result in response.results)


def test_results_carry_snippets_highlights_and_matched_terms(engine):
    response = engine.retrieve("weekly market")
    top = response.results[0]

    assert top.title
    assert top.host == "site-b.test"
    assert "market" in top.snippet.lower()
    assert top.highlights
    assert stem("market") in top.matched_terms


def test_stopword_only_query_returns_nothing(engine):
    response = engine.retrieve("the of and")
    assert response.results == []


def test_unknown_term_returns_nothing(engine):
    response = engine.retrieve("zeppelin")
    assert response.results == []


def test_inflected_query_matches_stemmed_index(engine):
    response = engine.retrieve("attractions", use_rm3=False)
    urls = [result.url for result in response.results]
    assert "https://site-c.test/attractions" in urls


def test_top_n_limits_results(engine):
    response = engine.retrieve("tübingen castle market food river")
    assert len(response.results) <= 100
    limited = engine.retrieve("castle", top_n=2)
    assert len(limited.results) == 2


def test_suggestions_built_from_expansion_terms(engine):
    response = engine.retrieve("castle")
    suggestions = engine.suggest_queries("castle", response.expansion_terms)
    assert suggestions
    assert all(suggestion.startswith("castle ") for suggestion in suggestions)
