from tuebingen_crawler.link_classifier import (
    LINK_FEATURE_WEIGHTS,
    LINK_THRESHOLD,
    MAX_DEPTH,
    classify_link,
    link_score,
    should_enqueue,
)
from tuebingen_crawler.models import REL_THRESHOLD


def test_link_score_normalizes_parent_www_host():
    score = link_score(
        anchor="About",
        url="https://uni-tuebingen.de/about",
        parent_relevance=REL_THRESHOLD,
        parent_host="www.uni-tuebingen.de",
    )

    expected = (
        LINK_FEATURE_WEIGHTS["url_has_tuebingen"]
        + LINK_FEATURE_WEIGHTS["parent_relevant"]
        + LINK_FEATURE_WEIGHTS["internal_link"]
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

    assert score == LINK_FEATURE_WEIGHTS["url_has_tuebingen"]


def test_link_score_does_not_chase_republic_url():
    # /Czech_Republic with a generic anchor gains no tuebingen url/anchor bonus.
    score = link_score(
        anchor="Czech Republic",
        url="https://en.wikipedia.org/wiki/Czech_Republic",
        parent_relevance=0.0,
        parent_host="en.wikipedia.org",
    )
    # only the internal_link feature may apply, never the tuebingen features
    assert score <= LINK_FEATURE_WEIGHTS["internal_link"]


def test_link_score_skips_resource_urls():
    score = link_score(
        anchor="Tübingen photo",
        url="https://www.tuebingen.de/image.jpg",
        parent_relevance=REL_THRESHOLD,
        parent_host="www.tuebingen.de",
    )
    assert score == 0.0


def test_should_enqueue_respects_threshold_and_depth():
    assert should_enqueue(LINK_THRESHOLD, MAX_DEPTH)
    assert not should_enqueue(LINK_THRESHOLD - 0.1, 1)
    assert not should_enqueue(LINK_THRESHOLD, MAX_DEPTH + 1)


def test_classify_link_enqueues_relevant_link():
    verdict = classify_link(
        anchor="Tübingen attractions",
        url="https://uni-tuebingen.de/tuebingen-attractions",
        parent_relevance=REL_THRESHOLD,
        parent_host="uni-tuebingen.de",
        depth=1,
    )

    assert verdict.url == "https://uni-tuebingen.de/tuebingen-attractions"
    assert verdict.score >= LINK_THRESHOLD
    assert verdict.enqueue


def test_classify_link_rejects_resource_url():
    verdict = classify_link(
        anchor="Tübingen photo",
        url="https://www.tuebingen.de/image.jpg",
        parent_relevance=REL_THRESHOLD,
        parent_host="www.tuebingen.de",
        depth=1,
    )

    assert verdict.score == 0.0
    assert not verdict.enqueue


def test_classify_link_rejects_too_deep_link():
    verdict = classify_link(
        anchor="Tübingen attractions",
        url="https://uni-tuebingen.de/tuebingen-attractions",
        parent_relevance=REL_THRESHOLD,
        parent_host="uni-tuebingen.de",
        depth=MAX_DEPTH + 1,
    )

    assert verdict.score >= LINK_THRESHOLD
    assert not verdict.enqueue
