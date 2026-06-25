from __future__ import annotations

import sqlite3
from pathlib import Path

from tuebingen_search.load_pages import PageLoad


def make_page_load(db_path: Path, pages: dict[Path, str | None]) -> PageLoad:
    con = sqlite3.connect(db_path)
    con.execute(
        """
        CREATE TABLE pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            host TEXT NOT NULL,
            path TEXT NOT NULL,
            status_code INTEGER,
            content_type TEXT,
            crawl_depth INTEGER,
            language TEXT,
            relevance REAL,
            token_count INTEGER,
            fetched_at TEXT NOT NULL,
            indexed_at TEXT
        )
        """
    )
    for path, content_type in pages.items():
        con.execute(
            """
            INSERT INTO pages (
                title, url, host, path, status_code, content_type,
                crawl_depth, language, relevance, token_count, fetched_at, indexed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                path.stem,
                f"https://example.test/{path.name}",
                "example.test",
                str(path),
                200,
                content_type,
                0,
                "en",
                5.0,
                100,
                "2026-01-01T00:00:00Z",
                None,
            ),
        )
    con.commit()
    con.close()
    return PageLoad(db_path)
