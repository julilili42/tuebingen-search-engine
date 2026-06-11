from tuebingen_crawler.relevance import is_page_relevant, mentions_tuebingen, url_priority

SEED_HOSTS = frozenset({"www.tuebingen.de"})


def test_mentions_counts_spelling_variants():
    assert mentions_tuebingen("Tübingen, Tuebingen and Tubingen") == 3


def test_relevant_when_url_or_title_mentions_tuebingen():
    assert is_page_relevant("https://example.com/tuebingen-guide", "", "")
    assert is_page_relevant("https://example.com/guide", "Visiting Tübingen", "")


def test_relevant_needs_repeated_mentions_in_body():
    assert not is_page_relevant("https://example.com/a", "Travel", "Tübingen once")
    text = "Tübingen is nice. Tübingen has a castle. Visit Tübingen!"
    assert is_page_relevant("https://example.com/a", "Travel", text)


def test_url_priority_prefers_tuebingen_and_seed_hosts():
    tuebingen_url = url_priority(
        "https://blog.example.com/tuebingen", True, SEED_HOSTS, "blog.example.com"
    )
    other_url = url_priority(
        "https://blog.example.com/munich", True, SEED_HOSTS, "blog.example.com"
    )
    seed_url = url_priority(
        "https://www.tuebingen.de/en/page", True, SEED_HOSTS, "www.tuebingen.de"
    )
    assert tuebingen_url > other_url
    assert seed_url > other_url


def test_url_priority_penalizes_deep_paths():
    shallow = url_priority("https://example.com/a", True, SEED_HOSTS, "example.com")
    deep = url_priority(
        "https://example.com/a/b/c/d/e/f", True, SEED_HOSTS, "example.com"
    )
    assert shallow > deep
