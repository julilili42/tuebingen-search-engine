"""Offline exporters that turn crawler output into relabeling CSVs.

These read the crawler's pages.sqlite (via tuebingen_crawler.save_pages.CrawlExportDB)
and emit CSVs that get re-imported into the labeling UI. They live here, not in
the crawler runtime package, so the crawler stays free of labeling/export logic.
"""
