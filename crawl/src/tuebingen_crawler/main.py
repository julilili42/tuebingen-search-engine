from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .crawler import crawl
from .models import CrawlConfig

logger = logging.getLogger(__name__)

# English content about Tübingen: official city/university pages, travel
# guides, encyclopedias and local English-language news.
DEFAULT_SEEDS = [
    "https://en.wikipedia.org/wiki/T%C3%BCbingen",
    "https://en.wikivoyage.org/wiki/T%C3%BCbingen",
    "https://www.tuebingen.de/en/",
    "https://www.tuebingen-info.de/en",
    "https://uni-tuebingen.de/en/",
    "https://www.unimuseum.uni-tuebingen.de/en/",
    "https://www.germany.travel/en/cities-culture/tuebingen.html",
    "https://historicgermany.travel/historic-germany/tubingen/",
    "https://www.komoot.com/guide/355570/castles-in-tuebingen-district",
    "https://www.outdooractive.com/en/places-to-see/tuebingen/",
    "https://www.thecrazytourist.com/15-best-things-to-do-in-tubingen-germany/",
    "https://velvetescape.com/things-to-do-in-tubingen/",
    "https://integreat.app/tuebingen/en",
    "https://tunewsinternational.com/category/news-in-english/",
    "https://www.tuebingen.mpg.de/en",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tuebingen-crawl",
        description="Crawl the web for English content about Tübingen.",
    )
    parser.add_argument(
        "-s", "--seeds", type=Path, default=None,
        help="File with one seed URL per line (default: built-in seed list)",
    )
    parser.add_argument(
        "-d", "--save-dir", default="data/crawl",
        help="Directory for crawled HTML, pages.jsonl and crawl state",
    )
    parser.add_argument(
        "-n", "--max-pages", type=int, default=5000,
        help="Stop after this many stored pages",
    )
    parser.add_argument(
        "--max-pages-per-host", type=int, default=800,
        help="Cap stored pages per host to keep the corpus diverse",
    )
    parser.add_argument(
        "--host-delay", type=float, default=1.0,
        help="Minimum seconds between requests to the same host",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def read_seeds(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    if not args.verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)

    seeds = read_seeds(args.seeds) if args.seeds else DEFAULT_SEEDS
    config = CrawlConfig(
        seeds=seeds,
        save_dir=args.save_dir,
        max_pages=args.max_pages,
        max_pages_per_host=args.max_pages_per_host,
        host_delay=args.host_delay,
    )

    try:
        statistics = crawl(config)
    except KeyboardInterrupt:
        logger.info("Interrupted; state was saved, re-run to resume.")
        return

    logger.info("Done: %s", statistics.summary())


if __name__ == "__main__":
    main()
