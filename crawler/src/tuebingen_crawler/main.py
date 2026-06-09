from __future__ import annotations

from pathlib import Path
from .crawler import crawl, save_jsonl
from .models import Config, CrawlSite

def main() -> None:
    tuepedia = CrawlSite()
    wiki_tuebingen = CrawlSite(url="https://de.wikipedia.org/wiki/T%C3%BCbingen")
    config = Config(sites=[wiki_tuebingen, tuepedia])
    
    try:
        index = crawl(config)
    except Exception as exc:
        print(f"ERROR: failed to crawl with error {exc}")
        return

    jsonl_path = Path(config.save_dir) / "index.jsonl"
    try:
        save_jsonl(jsonl_path, index)
    except Exception as exc:
        print(f"ERROR: failed to save jsonl file with error {exc}")
        return

if __name__ == "__main__":
    main()
