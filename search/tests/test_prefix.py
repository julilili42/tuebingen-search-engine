import pytest

from tuebingen_search.search import SearchEngine
from tuebingen_search.tokenizer import stem


@pytest.fixture(scope="session")
def engine(index_path) -> SearchEngine:
    return SearchEngine(index_path)


def test_unfinished_word_finds_completions(engine):
    # "tübin" is not a token in any document, but completes to "tübingen".
    response = engine.retrieve("tübin")
    assert "tübingen" in response.completions
    assert response.results


def test_prefix_results_highlight_completed_term(engine):
    response = engine.retrieve("tübin")
    assert "tübingen" in response.results[0].matched_terms
    # Results whose body text contains the completed word highlight it
    # (title-only matches have nothing to highlight in the snippet).
    assert any(
        result.snippet[start:end].lower() == "tübingen"
        for result in response.results
        for start, end in result.highlights
    )


def test_typed_text_longer_than_stem_still_matches(engine):
    # The stem of "attractions" is "attract"; a half-typed "attracti" extends
    # past it and must still find the attractions page.
    response = engine.retrieve("attracti")
    assert stem("attraction") in response.completions
    assert any(
        result.url == "https://site-c.test/attractions"
        for result in response.results
    )


def test_finished_words_are_unaffected(engine):
    with_prefix = engine.retrieve("castle", use_rm3=False, use_mmr=False)
    without_prefix = engine.retrieve(
        "castle", use_rm3=False, use_mmr=False, use_prefix=False
    )
    assert [r.url for r in with_prefix.results] == [
        r.url for r in without_prefix.results
    ]


def test_stopword_last_token_skips_completion(engine):
    response = engine.retrieve("castle the")
    assert response.completions == []
    assert response.results


def test_unknown_prefix_still_returns_nothing(engine):
    response = engine.retrieve("zeppelin")
    assert response.completions == []
    assert response.results == []


def test_prefix_disabled_for_unfinished_word(engine):
    response = engine.retrieve("tübin", use_prefix=False)
    assert response.results == []
