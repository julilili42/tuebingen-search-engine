from tuebingen_crawler.urls import host_of, is_blocked_host, normalize_url, url_slug


def test_normalize_resolves_relative_urls():
    assert (
        normalize_url("../about", "https://example.com/en/city/")
        == "https://example.com/en/about"
    )


def test_normalize_drops_fragment_and_query():
    assert (
        normalize_url("https://example.com/page?session=42#top")
        == "https://example.com/page"
    )


def test_normalize_lowercases_host_and_strips_trailing_slash():
    assert normalize_url("https://Example.COM/Page/") == "https://example.com/Page"


def test_normalize_keeps_root_slash():
    assert normalize_url("https://example.com/") == "https://example.com/"


def test_normalize_strips_default_port_keeps_custom_port():
    assert normalize_url("https://example.com:443/a") == "https://example.com/a"
    assert normalize_url("https://example.com:8443/a") == "https://example.com:8443/a"


def test_normalize_rejects_non_http_schemes():
    assert normalize_url("mailto:test@example.com") is None
    assert normalize_url("javascript:void(0)") is None


def test_normalize_rejects_media_files():
    assert normalize_url("https://example.com/photo.JPG") is None
    assert normalize_url("https://example.com/doc.pdf") is None
    assert normalize_url("https://example.com/page.html") is not None


def test_normalize_rejects_blocked_hosts():
    assert normalize_url("https://www.facebook.com/tuebingen") is None
    assert is_blocked_host("m.youtube.com")
    assert not is_blocked_host("tuebingen.de")


def test_host_of():
    assert host_of("https://EN.Wikipedia.org/wiki/T%C3%BCbingen") == "en.wikipedia.org"


def test_url_slug_sanitizes_and_truncates():
    assert url_slug("https://example.com/en/city-hall") == "en-city-hall"
    assert url_slug("https://example.com/") == "index"
    long_url = "https://example.com/" + "a" * 200
    assert len(url_slug(long_url)) <= 90
