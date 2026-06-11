"""End-to-end crawl against a mocked HTTP transport."""

import json

import httpx
import pytest

import tuebingen_crawler.crawler as crawler_module
from tuebingen_crawler.crawler import crawl
from tuebingen_crawler.models import CrawlConfig

ENGLISH_PARAGRAPH = (
    "<p>Tübingen is a university town in Germany. The old town of Tübingen "
    "is known for its narrow alleys and the castle above the river. Many "
    "people visit Tübingen for the market square and the botanical garden "
    "that has been part of the university for a very long time.</p>"
)

GERMAN_PARAGRAPH = (
    "<p>Tübingen ist eine Universitätsstadt in Deutschland. Die Altstadt von "
    "Tübingen ist bekannt für ihre engen Gassen und das Schloss über dem "
    "Fluss, das man von vielen Orten der Stadt aus sehen kann und das von "
    "den Studierenden der Universität gerne besucht wird.</p>"
)

PAGES = {
    "https://site-a.test/": (
        f"<html lang='en'><head><title>Tübingen Guide</title></head><body>"
        f"{ENGLISH_PARAGRAPH}"
        f"<a href='/english'>english page</a>"
        f"<a href='/german'>german page</a>"
        f"<a href='/offtopic'>other</a>"
        f"<a href='https://blocked.test/page'>blocked</a></body></html>"
    ),
    "https://site-a.test/english": (
        f"<html lang='en'><head><title>Old town of Tübingen</title></head>"
        f"<body>{ENGLISH_PARAGRAPH}</body></html>"
    ),
    "https://site-a.test/german": (
        f"<html lang='de'><head><title>Altstadt Tübingen</title></head>"
        f"<body>{GERMAN_PARAGRAPH}</body></html>"
    ),
    "https://site-a.test/offtopic": (
        "<html lang='en'><head><title>Generic travel news</title></head><body>"
        "<p>This page is about travelling in general. It talks about the best "
        "ways to pack a bag for a longer trip and how to find cheap tickets "
        "for trains in Europe during the busy summer season.</p></body></html>"
    ),
}


def handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.endswith("/robots.txt"):
        return httpx.Response(404)
    if url in PAGES:
        return httpx.Response(
            200, content=PAGES[url].encode(), headers={"Content-Type": "text/html"}
        )
    return httpx.Response(404)


@pytest.fixture
def mock_http(monkeypatch):
    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def client_factory(**kwargs):
        kwargs.pop("transport", None)
        return real_client(transport=transport, **kwargs)

    monkeypatch.setattr(crawler_module.httpx, "Client", client_factory)


def make_config(tmp_path, **overrides) -> CrawlConfig:
    defaults = dict(
        seeds=["https://site-a.test/"],
        save_dir=str(tmp_path / "crawl"),
        max_pages=10,
        host_delay=0.0,
        save_state_every=1,
    )
    defaults.update(overrides)
    return CrawlConfig(**defaults)


def saved_urls(tmp_path) -> set[str]:
    pages_file = tmp_path / "crawl" / "pages.jsonl"
    if not pages_file.exists():
        return set()
    return {
        json.loads(line)["url"]
        for line in pages_file.read_text().splitlines()
        if line.strip()
    }


def test_crawl_stores_only_relevant_english_pages(tmp_path, mock_http):
    statistics = crawl(make_config(tmp_path))

    urls = saved_urls(tmp_path)
    assert urls == {"https://site-a.test/", "https://site-a.test/english"}
    assert statistics.skipped_language == 1  # the German page
    assert statistics.skipped_relevance == 1  # the off-topic page


def test_crawl_is_resumable(tmp_path, mock_http):
    # First run stores only the seed page.
    crawl(make_config(tmp_path, max_pages=1))
    assert saved_urls(tmp_path) == {"https://site-a.test/"}

    # Second run picks up the frontier and finds the remaining page.
    crawl(make_config(tmp_path, max_pages=10))
    assert "https://site-a.test/english" in saved_urls(tmp_path)


def test_crawl_respects_max_pages_per_host(tmp_path, mock_http):
    crawl(make_config(tmp_path, max_pages_per_host=1))
    assert len(saved_urls(tmp_path)) == 1
