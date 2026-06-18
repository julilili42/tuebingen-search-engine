import tuebingen_crawler.heuristic as heuristic
from tuebingen_crawler.heuristic import Language, detect_language, link_score


def test_detect_language_uses_lang_attribute_without_loading_stopwords(monkeypatch):
    def fail_load_stopwords():
        raise AssertionError("stopwords should not be loaded for short text")

    monkeypatch.setattr(heuristic, "load_stopwords", fail_load_stopwords)

    assert detect_language("short text", "en") is Language.EN


def test_detect_language_uses_cached_nltk_stopwords(monkeypatch):
    monkeypatch.setattr(heuristic, "_STOPWORDS", ({"und", "der"}, {"the", "and"}))

    text = " ".join(
        [
            "the", "and", "the", "and", "the", "and",
            "university", "town", "river", "city", "history",
        ]
        * 3
    )

    assert detect_language(text) is Language.EN


def test_link_score_normalizes_parent_www_host():
    score = link_score(
        anchor="About",
        url="https://uni-tuebingen.de/about",
        parent_relevance=3.0,
        parent_host="www.uni-tuebingen.de",
    )

    expected = (
        heuristic.LINK_FEATURE_WEIGHTS["url_has_tuebingen"]
        + heuristic.LINK_FEATURE_WEIGHTS["parent_relevant"]
        + heuristic.LINK_FEATURE_WEIGHTS["internal_link"]
    )
    assert score == expected


def test_link_score_does_not_prefer_known_hosts_without_tuebingen_terms():
    known_host_score = link_score(
        anchor="About",
        url="https://tuepedia.de/about",
        parent_relevance=0.0,
        parent_host="example.com",
    )
    unknown_host_score = link_score(
        anchor="About",
        url="https://example.com/about",
        parent_relevance=0.0,
        parent_host="other.example",
    )

    assert known_host_score == unknown_host_score == 0.0


def test_link_score_still_uses_tuebingen_terms_in_url():
    score = link_score(
        anchor="About",
        url="https://uni-tuebingen.de/about",
        parent_relevance=0.0,
        parent_host="example.com",
    )

    assert score == heuristic.LINK_FEATURE_WEIGHTS["url_has_tuebingen"]
