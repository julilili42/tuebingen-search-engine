from __future__ import annotations

import argparse
from pathlib import Path

from tuebingen_crawler.paths import DEFAULT_DATA_DIR, DEFAULT_DB_PATH
from tuebingen_crawler.save_pages import CrawlExportDB


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export crawler link decisions for relabeling"
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_DATA_DIR / "link_candidates.csv",
    )
    args = parser.parse_args()

    with CrawlExportDB(args.db) as store:
        store.export_linkverdict_csv(args.out)

    print(args.out)


if __name__ == "__main__":
    main()
