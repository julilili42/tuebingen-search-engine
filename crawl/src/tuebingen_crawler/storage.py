from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path

from .models import CrawlState, PageRecord, Statistics

logger = logging.getLogger(__name__)

STATE_FILE = "crawl_state.json"
PAGES_FILE = "pages.jsonl"


def state_path(save_dir: str) -> Path:
    return Path(save_dir) / STATE_FILE


def pages_path(save_dir: str) -> Path:
    return Path(save_dir) / PAGES_FILE


def save_state(save_dir: str, state: CrawlState) -> None:
    """Atomically persist the crawl state (write to tmp file, then rename)."""
    path = state_path(save_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps(asdict(state)), encoding="utf-8")
    os.replace(tmp_path, path)


def load_state(save_dir: str) -> CrawlState | None:
    path = state_path(save_dir)
    if not path.exists():
        return None

    data = json.loads(path.read_text(encoding="utf-8"))
    state = CrawlState(
        frontier=data.get("frontier", []),
        next_seq=data.get("next_seq", 0),
        seen=data.get("seen", []),
        saved_urls=data.get("saved_urls", []),
        host_pages=data.get("host_pages", {}),
        statistics=Statistics(**data.get("statistics", {})),
    )
    logger.info(
        "Resuming crawl: %d queued, %d seen, %d saved",
        len(state.frontier), len(state.seen), len(state.saved_urls),
    )
    return state


def append_page_record(save_dir: str, record: PageRecord) -> None:
    """Append one stored page to pages.jsonl (the crawl's document catalog)."""
    path = pages_path(save_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as pages_file:
        pages_file.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def load_page_records(save_dir: str) -> list[PageRecord]:
    path = pages_path(save_dir)
    if not path.exists():
        return []

    records = []
    with path.open("r", encoding="utf-8") as pages_file:
        for line in pages_file:
            line = line.strip()
            if line:
                records.append(PageRecord(**json.loads(line)))
    return records
