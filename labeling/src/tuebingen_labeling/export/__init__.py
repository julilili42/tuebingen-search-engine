"""Offline exporters that turn crawler output into relabeling JSONL.

These read the crawler's pages.sqlite (via tuebingen_crawler.save_pages.CrawlExportDB)
and emit JSONL that gets re-imported into the labeling UI. They live here, not in
the crawler runtime package, so the crawler stays free of labeling/export logic.
"""
