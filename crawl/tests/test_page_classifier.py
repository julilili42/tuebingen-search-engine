import tuebingen_crawler.page_classifier as page_classifier
from tuebingen_crawler.models import Language, REL_THRESHOLD
from tuebingen_crawler.page_classifier import (
    PageIndexExclusion,
    SEMANTIC_CONFIG,
    classify_page,
    detect_language,
    lexical_relevance_score,
)


# --- language detection ------------------------------------------------------

def test_detect_language_uses_lang_attribute_without_loading_stopwords(monkeypatch):
    def fail_load_stopwords():
        raise AssertionError("stopwords should not be loaded for short text")

    monkeypatch.setattr(page_classifier, "load_stopwords", fail_load_stopwords)

    assert detect_language(["short", "text"], "en") is Language.EN


def test_detect_language_uses_cached_nltk_stopwords(monkeypatch):
    monkeypatch.setattr(page_classifier, "_STOPWORDS", ({"und", "der"}, {"the", "and"}))

    tokens = [
        "the", "and", "the", "and", "the", "and",
        "university", "town", "river", "city", "history",
    ] * 3

    assert detect_language(tokens) is Language.EN


def test_detect_language_trusts_non_english_lang_attribute(monkeypatch):
    def fail_load_stopwords():
        raise AssertionError("stopwords should not decide when lang is declared")

    monkeypatch.setattr(page_classifier, "load_stopwords", fail_load_stopwords)

    english_looking = ["a", "i", "o", "it", "do", "as"] * 20
    assert detect_language(english_looking, "cs") is Language.UNKNOWN


# --- topic-drift regression tests -------------------------------------------

def test_lexical_relevance_substring_pub_in_republic_does_not_count():
    # "pub" must not match inside "Republic"/"Public"; without a core Tübingen
    # term the page is not relevant at all.
    body = "The Czech Republic is a country in central Europe with many pubs. " * 5
    assert lexical_relevance_score(
        "https://en.wikipedia.org/wiki/Czech_Republic", "Czech Republic", body
    ) == 0.0


def test_lexical_relevance_generic_terms_alone_do_not_qualify():
    body = ("This list ranks restaurants and hotels. Restaurant, restaurant, "
            "hotel, cafe, bistro, brewery, pub. ") * 10
    assert lexical_relevance_score(
        "https://en.wikipedia.org/wiki/List_of_restaurants",
        "List of Michelin-starred restaurants", body,
    ) == 0.0


def test_lexical_relevance_keeps_real_tuebingen_page():
    body = ("Tübingen is a university town on the river Neckar. The old town of "
            "Tübingen and the university of Tübingen attract many visitors. ") * 5
    score = lexical_relevance_score(
        "https://en.wikipedia.org/wiki/T%C3%BCbingen", "Tübingen", body
    )
    assert score >= REL_THRESHOLD


def test_lexical_relevance_named_entity_without_word_tuebingen_qualifies():
    # Bebenhausen is a Tübingen district; should qualify via the named-core list.
    body = ("Bebenhausen Abbey is a former Cistercian monastery near the town. "
            "The Bebenhausen monastery is a popular destination. ") * 5
    score = lexical_relevance_score(
        "https://en.wikipedia.org/wiki/Bebenhausen_Abbey", "Bebenhausen Abbey", body
    )
    assert score >= REL_THRESHOLD


def test_lexical_relevance_title_only_match_qualifies():
    # a page titled about Tübingen counts even with a neutral body (recall)
    body = "A museum showing art, coins and prehistoric artefacts to its visitors. " * 5
    score = lexical_relevance_score(
        "https://example.com/museum", "Tübingen City Museum", body
    )
    assert score >= REL_THRESHOLD


def test_lexical_relevance_single_incidental_mention_is_filtered():
    # one passing mention of Tübingen in an otherwise off-topic page is too weak
    body = ("This article is about German universities in general. "
            "Heidelberg, Munich and Tübingen are mentioned once. ") + (
            "Universities educate students across many disciplines. " * 30)
    score = lexical_relevance_score(
        "https://example.com/german-universities", "German universities", body
    )
    assert score < REL_THRESHOLD


# --- semantic modulation of the page relevance ------------------------------

_TUEBINGEN_URL = "https://en.wikipedia.org/wiki/T%C3%BCbingen"
_TUEBINGEN_BODY = (
    "Tübingen is a university town on the river Neckar. The old town of "
    "Tübingen and the university of Tübingen attract many visitors. "
) * 5


def test_classify_page_rejects_offtopic_english_page(monkeypatch):
    # an English page without a lexical signal is run through the model, but a
    # low similarity keeps it out of the index.
    monkeypatch.setattr(page_classifier, "topic_similarity", lambda title, text: 0.3)

    verdict = classify_page(
        "https://example.com/czech", "Czech Republic", "A country in Europe. " * 10
    )
    assert verdict.relevance == 0.0


def test_classify_page_high_similarity_keeps_lexical_score(monkeypatch):
    monkeypatch.setattr(page_classifier, "topic_similarity", lambda title, text: 1.0)

    lexical = lexical_relevance_score(_TUEBINGEN_URL, "Tübingen", _TUEBINGEN_BODY)
    verdict = classify_page(_TUEBINGEN_URL, "Tübingen", _TUEBINGEN_BODY, "en")

    assert verdict.relevance == lexical


def test_classify_page_low_similarity_demotes_to_floor(monkeypatch):
    monkeypatch.setattr(page_classifier, "topic_similarity", lambda title, text: 0.0)

    lexical = lexical_relevance_score(_TUEBINGEN_URL, "Tübingen", _TUEBINGEN_BODY)
    verdict = classify_page(_TUEBINGEN_URL, "Tübingen", _TUEBINGEN_BODY, "en")

    assert verdict.relevance == lexical * SEMANTIC_CONFIG.lexical_floor


def test_classify_page_model_can_demote_borderline_page_below_threshold(monkeypatch):
    # a url-only match that the model finds off-topic should drop below the
    # relevance threshold.
    monkeypatch.setattr(page_classifier, "topic_similarity", lambda title, text: 0.0)

    body = "An unrelated article about something else entirely. " * 10
    verdict = classify_page("https://www.tuebingen.de/hotel-booking", "Booking", body, "en")

    assert 0.0 < verdict.relevance < REL_THRESHOLD


def test_classify_page_does_not_keep_short_relevant_english_page(monkeypatch):
    monkeypatch.setattr(page_classifier, "topic_similarity", lambda title, text: 1.0)

    verdict = classify_page("https://example.com/short", "Tübingen", "Short note.", "en")

    assert verdict.is_english
    assert verdict.is_relevant
    assert not verdict.has_enough_text
    assert verdict.should_follow_links
    assert not verdict.should_index
    assert verdict.index_exclusion is PageIndexExclusion.TOO_SHORT


def test_short_relevant_page_is_too_short_before_non_english(monkeypatch):
    monkeypatch.setattr(page_classifier, "topic_similarity", lambda title, text: 1.0)

    verdict = classify_page("https://example.com/short", "Tübingen", "Kurzer Text.", "de")

    assert verdict.is_relevant
    assert verdict.index_exclusion is PageIndexExclusion.TOO_SHORT


# --- semantic admission of pages without any lexical signal ------------------

# a page with no "Tübingen"/named-entity term anywhere -> lexical score is 0
_TOKENLESS_URL = "https://example.com/old-town"
_TOKENLESS_BODY = "The old town has a market square, half-timbered houses and a castle. " * 5


def test_classify_page_admits_tokenless_english_page_on_high_similarity(monkeypatch):
    monkeypatch.setattr(page_classifier, "topic_similarity", lambda title, text: 0.9)

    verdict = classify_page(_TOKENLESS_URL, "Old Town", _TOKENLESS_BODY, "en")

    assert verdict.relevance >= REL_THRESHOLD
    # stays below strong lexical hits
    assert verdict.relevance <= REL_THRESHOLD + SEMANTIC_CONFIG.admit_span


def test_classify_page_rejects_tokenless_english_page_on_low_similarity(monkeypatch):
    monkeypatch.setattr(page_classifier, "topic_similarity", lambda title, text: 0.4)

    verdict = classify_page(_TOKENLESS_URL, "Old Town", _TOKENLESS_BODY, "en")

    assert verdict.relevance == 0.0


def test_classify_page_skips_model_for_tokenless_non_english_page(monkeypatch):
    def fail_similarity(title, text):
        raise AssertionError("model must not run on non-English pages without lexical signal")

    monkeypatch.setattr(page_classifier, "topic_similarity", fail_similarity)

    # short body + lang attribute -> detected as German without loading stopwords
    verdict = classify_page(_TOKENLESS_URL, "Altstadt", "Kurzer Text.", "de")

    assert verdict.relevance == 0.0
