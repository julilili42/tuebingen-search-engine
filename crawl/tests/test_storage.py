from tuebingen_crawler.models import CrawlState, PageRecord, Statistics
from tuebingen_crawler.storage import (
    append_page_record,
    load_page_records,
    load_state,
    save_state,
)


def test_state_roundtrip(tmp_path):
    save_dir = str(tmp_path)
    state = CrawlState(
        frontier=[[-2.0, 0, "https://a.com/1"]],
        next_seq=1,
        seen=["https://a.com/1"],
        saved_urls=["https://a.com/0"],
        host_pages={"a.com": 1},
        statistics=Statistics(fetched=3, saved=1),
    )

    save_state(save_dir, state)
    loaded = load_state(save_dir)

    assert loaded == state


def test_load_state_returns_none_when_missing(tmp_path):
    assert load_state(str(tmp_path)) is None


def test_page_records_append_and_load(tmp_path):
    save_dir = str(tmp_path)
    first = PageRecord(url="https://a.com/1", path="a/1.html", title="One", description="d1")
    second = PageRecord(url="https://a.com/2", path="a/2.html", title="Twö", description="")

    append_page_record(save_dir, first)
    append_page_record(save_dir, second)

    assert load_page_records(save_dir) == [first, second]


def test_load_page_records_empty(tmp_path):
    assert load_page_records(str(tmp_path)) == []
