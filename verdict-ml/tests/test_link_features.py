from verdict_ml.link.features import (
    LinkFeatureConfig,
    LinkVerdictInput,
    host_from_url,
    is_skipable_link,
    make_text,
    normalize_host,
    path_text,
)


def test_normalize_host_removes_www_and_lowercases():
    assert normalize_host("WWW.Example.ORG") == "example.org"
    assert normalize_host(None) == ""


def test_url_helpers_extract_host_and_path_text():
    assert host_from_url("https://www.example.org/en/tuebingen-guide.html") == "example.org"
    assert path_text("https://example.org/en/tuebingen-guide.html") == "en tuebingen guide html"


def test_is_skipable_link_flags_hard_skip_urls():
    assert is_skipable_link("https://example.org/files/map.pdf")
    assert is_skipable_link("https://twitter.com/example/status/1")
    assert is_skipable_link("https://example.org/de/tuebingen")
    assert not is_skipable_link("https://example.org/en/tuebingen")


def test_is_skipable_link_accepts_custom_config():
    config = LinkFeatureConfig(
        resource_suffixes=(".bin",),
        skip_path_words=frozenset({"skipme"}),
        non_english_language_prefixes=frozenset({"xx"}),
        blocked_hosts=frozenset({"blocked.test"}),
        blocked_host_suffixes=(".blocked.test",),
    )

    assert is_skipable_link("https://blocked.test/page", config)
    assert is_skipable_link("https://example.test/file.bin", config)
    assert is_skipable_link("https://example.test/xx/page", config)
    assert is_skipable_link("https://example.test/path/skipme", config)
    assert not is_skipable_link("https://example.test/de/page", config)


def test_make_text_includes_bucketed_metadata_and_skip_flag():
    text = make_text(
        LinkVerdictInput(
            anchor=" Official  page ",
            target_url="https://example.org/tuebingen.pdf",
            parent_url="https://parent.test/start",
            parent_depth=1,
            parent_pageverdict_score=0.84,
            parent_pageverdict_decision="keep",
            parent_relevance=2.7,
            target_depth=2,
        )
    )

    assert "anchor: Official page" in text
    assert "target_host: example.org" in text
    assert "parent_depth: 1" in text
    assert "target_depth: 2" in text
    assert "parent_pageverdict_score_bucket: 0.80" in text
    assert "parent_relevance_bucket: 2.50" in text
    assert "flags: hard_skipable_url:yes" in text
