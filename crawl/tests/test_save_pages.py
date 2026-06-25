import sqlite3

from tuebingen_crawler.save_pages import PageStore


def test_page_store_creates_fetched_and_indexed_at_as_last_columns(tmp_path):
    with PageStore(tmp_path / "pages.sqlite") as store:
        columns = [
            row["name"]
            for row in store.con.execute("PRAGMA table_info(pages)").fetchall()
        ]

    assert columns[-2:] == ["fetched_at", "indexed_at"]


def test_page_store_migrates_existing_db_without_title(tmp_path):
    db_path = tmp_path / "pages.sqlite"
    con = sqlite3.connect(db_path)
    con.execute(
        """
        CREATE TABLE pages (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            host TEXT NOT NULL,
            path TEXT NOT NULL,
            status_code INTEGER,
            content_type TEXT,
            fetched_at TEXT NOT NULL,
            indexed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    con.execute(
        """
        INSERT INTO pages (
            url, host, path, status_code, content_type, fetched_at, indexed_at, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "https://host/",
            "host",
            str(tmp_path / "host" / "index.html"),
            200,
            "text/html",
            "2026-01-01T00:00:00+00:00",
            None,
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
        ),
    )
    con.commit()
    con.close()

    with PageStore(db_path) as store:
        [page] = list(store.iter_html_pages())

    assert page.title == ""
    assert page.url == "https://host/"
    assert page.crawl_depth is None
    assert page.language is None
    assert page.relevance is None
    assert page.token_count is None


def test_page_store_upsert_persists_page_metadata(tmp_path):
    with PageStore(tmp_path / "pages.sqlite") as store:
        store.upsert_page(
            title="Tuebingen",
            url="https://host/",
            host="host",
            path=tmp_path / "host" / "index.html",
            status_code=200,
            content_type="text/html",
            crawl_depth=2,
            language="en",
            relevance=7.5,
            token_count=123,
        )

        [page] = list(store.iter_html_pages())

    assert page.title == "Tuebingen"
    assert page.crawl_depth == 2
    assert page.language == "en"
    assert page.relevance == 7.5
    assert page.token_count == 123
