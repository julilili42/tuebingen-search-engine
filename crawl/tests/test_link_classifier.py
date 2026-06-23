import pytest

import tuebingen_crawler.link_classifier as link_classifier
from tuebingen_crawler.link_classifier import (
    FRONTIER_CONFIG,
    LINK_CONFIG,
    LinkVerdict,
    classify_link,
    link_score,
    semantic_link_score,
)
from tuebingen_crawler.models import REL_THRESHOLD


def test_link_score_normalizes_parent_www_host():
    score = link_score(
        anchor="About",
        url="https://uni-tuebingen.de/about",
        parent_relevance=REL_THRESHOLD,
        parent_host="www.uni-tuebingen.de",
    )

    # url cue + internal-link cue + the inherited parent term; at
    # parent_relevance == REL_THRESHOLD and depth 0 that term equals parent weight.
    expected = (
        LINK_CONFIG.feature_weights["url_has_tuebingen"]
        + LINK_CONFIG.feature_weights["internal_link"]
        + LINK_CONFIG.parent_relevance.weight
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

    assert score == LINK_CONFIG.feature_weights["url_has_tuebingen"]


def test_link_score_does_not_chase_republic_url():
    # /Czech_Republic with a generic anchor gains no tuebingen url/anchor bonus.
    score = link_score(
        anchor="Czech Republic",
        url="https://en.wikipedia.org/wiki/Czech_Republic",
        parent_relevance=0.0,
        parent_host="en.wikipedia.org",
    )
    # only the internal_link feature may apply, never the tuebingen features
    assert score <= LINK_CONFIG.feature_weights["internal_link"]


def test_link_score_skips_resource_urls():
    score = link_score(
        anchor="Tübingen photo",
        url="https://www.tuebingen.de/image.jpg",
        parent_relevance=REL_THRESHOLD,
        parent_host="www.tuebingen.de",
    )
    assert score == 0.0


def test_link_score_skips_web_archive_hosts():
    for host in LINK_CONFIG.blocked_hosts:
        score = link_score(
            anchor="Tübingen history",
            url=f"https://{host}/web/20240101/https://www.tuebingen.de/",
            parent_relevance=REL_THRESHOLD,
            parent_host=host,
        )

        assert score == 0.0


def test_semantic_link_score_uses_anchor_and_url_path(monkeypatch):
    def fake_similarity(title, text):
        assert title == ""
        assert "Old Town" in text
        assert "old town" in text
        return 0.85

    monkeypatch.setattr(link_classifier, "topic_similarity", fake_similarity)

    score = semantic_link_score("Old Town", "https://example.org/old-town")
    threshold = LINK_CONFIG.semantic.admit_threshold

    assert score == pytest.approx((0.85 - threshold) / (1.0 - threshold))


def test_link_score_semantic_signal_lifts_link_from_strong_parent(monkeypatch):
    monkeypatch.setattr(link_classifier, "topic_similarity", lambda title, text: 1.0)

    score = link_score(
        anchor="Old Town",
        url="https://example.org/old-town",
        parent_relevance=15.0,
        parent_host="host",
        depth=1,
    )

    assert score >= FRONTIER_CONFIG.threshold


def test_link_score_skips_semantic_signal_for_weak_parent(monkeypatch):
    def fail_similarity(title, text):
        raise AssertionError("semantic scoring should require a strong parent page")

    monkeypatch.setattr(link_classifier, "topic_similarity", fail_similarity)

    score = link_score(
        anchor="Old Town",
        url="https://example.org/old-town",
        parent_relevance=REL_THRESHOLD,
        parent_host="host",
        depth=1,
    )

    assert score < FRONTIER_CONFIG.threshold


def test_link_score_strong_parent_lifts_generic_internal_link():
    # a generic internal link (no tübingen cue in anchor or url) is worth following
    # from a strongly relevant parent, but not from a barely-relevant one.
    url = "https://example.org/research/some-institute"
    strong = link_score(
        "Read more", url, parent_relevance=15.0, parent_host="example.org", depth=1
    )
    weak = link_score(
        "Read more", url, parent_relevance=REL_THRESHOLD, parent_host="example.org", depth=1
    )

    assert strong >= FRONTIER_CONFIG.threshold
    assert weak < FRONTIER_CONFIG.threshold


def test_link_verdict_enqueue_respects_threshold_and_depth():
    assert LinkVerdict(
        url="https://example.com",
        score=FRONTIER_CONFIG.threshold,
        depth=FRONTIER_CONFIG.max_depth,
    ).enqueue
    assert not LinkVerdict(
        url="https://example.com",
        score=FRONTIER_CONFIG.threshold - 0.1,
        depth=1,
    ).enqueue
    assert not LinkVerdict(
        url="https://example.com",
        score=FRONTIER_CONFIG.threshold,
        depth=FRONTIER_CONFIG.max_depth + 1,
    ).enqueue


def test_classify_link_enqueues_relevant_link():
    verdict = classify_link(
        anchor="Tübingen attractions",
        url="https://uni-tuebingen.de/tuebingen-attractions",
        parent_relevance=REL_THRESHOLD,
        parent_host="uni-tuebingen.de",
        depth=1,
    )

    assert verdict.url == "https://uni-tuebingen.de/tuebingen-attractions"
    assert verdict.score >= FRONTIER_CONFIG.threshold
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
        depth=FRONTIER_CONFIG.max_depth + 1,
    )

    assert verdict.score >= FRONTIER_CONFIG.threshold
    assert not verdict.enqueue
