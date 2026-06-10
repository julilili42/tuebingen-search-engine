from __future__ import annotations

import logging
from pathlib import Path
from .crawler import crawl, save_jsonl
from .models import Config, CrawlSite

logger = logging.getLogger(__name__)

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    tuepedia = CrawlSite(url="https://www.tuepedia.de/", max_pages=1000)
    wiki_tuebingen = CrawlSite(url="https://de.wikipedia.org/wiki/T%C3%BCbingen", max_pages=1000)
    config = Config(sites=[wiki_tuebingen, tuepedia])
    
    try:
        index = crawl(config)
    except Exception as exc:
        logger.error("Failed to crawl with error %s", exc)
        return

    jsonl_path = Path(config.save_dir) / "index.jsonl"
    try:
        save_jsonl(jsonl_path, index)
    except Exception as exc:
        logger.error("Failed to save jsonl file with error %s", exc)
        return

if __name__ == "__main__":
    main()
