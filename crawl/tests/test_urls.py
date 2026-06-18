import pytest

from tuebingen_crawler.urls import (
    canonical_url,
    url_slug,
)


def test_canonical_url_removes_query_and_fragment():
    url, ok = canonical_url(
        "/wiki/Tübingen?x=1#top",
        "https://www.tuepedia.de/",
    )
    assert ok
    assert url == "https://www.tuepedia.de/wiki/Tübingen"

def test_canonical_url_keeps_other_hosts():
    # Cross-Domain: fremde Hosts werden nicht mehr verworfen
    url, ok = canonical_url(
        "https://example.com/page",
        "https://www.tuepedia.de/",
    )
    assert ok
    assert url == "https://example.com/page"

def test_canonical_url_resolves_relative_paths():
    url, ok = canonical_url(
        "subpage",
        "https://www.tuepedia.de/wiki/",
    )
    assert ok
    assert url == "https://www.tuepedia.de/wiki/subpage"

def test_canonical_url_strips_trailing_slash_except_root():
    url, ok = canonical_url(
        "/wiki/Tübingen/",
        "https://www.tuepedia.de/",
    )
    assert ok
    assert url == "https://www.tuepedia.de/wiki/Tübingen"

    root, ok = canonical_url(
        "https://www.tuepedia.de/",
        "https://www.tuepedia.de/",
    )
    assert ok
    assert root == "https://www.tuepedia.de/"

def test_canonical_url_lowercases_netloc():
    url, ok = canonical_url(
        "https://WWW.Tuepedia.DE/wiki/page",
        "https://www.tuepedia.de/",
    )
    assert ok
    assert url == "https://www.tuepedia.de/wiki/page"

@pytest.mark.parametrize("href", [
    "mailto:someone@example.com",
    "javascript:void(0)",
    "ftp://www.tuepedia.de/file",
])
def test_canonical_url_rejects_non_http_schemes(href):
    url, ok = canonical_url(href, "https://www.tuepedia.de/")
    assert not ok
    assert url == ""


def test_url_slug_basic_path():
    assert url_slug("https://www.tuepedia.de/wiki/Tübingen") == "wiki-tübingen"

def test_url_slug_root_becomes_index():
    assert url_slug("https://www.tuepedia.de/") == "index"

def test_url_slug_includes_query():
    slug = url_slug("https://host/search?q=test&page=2")
    assert slug == "search-q-test-page-2"

def test_url_slug_truncates_long_paths():
    slug = url_slug("https://host/" + "a" * 200)
    assert len(slug) <= 90

def test_url_slug_never_empty():
    assert url_slug("https://host/---") == "page"
