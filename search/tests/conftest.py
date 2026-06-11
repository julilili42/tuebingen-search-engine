import json

import pytest

from tuebingen_search.indexer import index

# Small English corpus about Tübingen; big enough for LSA (terms like
# "castle", "market", "food", "river" appear in >= 3 documents).
CORPUS = [
    (
        "https://site-a.test/castle",
        "Hohentübingen Castle",
        "The castle of Tübingen houses the university museum. The castle "
        "towers above the old town. Visitors love the castle museum and its "
        "ancient collection.",
    ),
    (
        "https://site-a.test/castle-garden",
        "Castle gardens",
        "The castle garden offers a view over the river. The museum inside "
        "the castle shows old scientific instruments.",
    ),
    (
        "https://site-b.test/restaurants",
        "Restaurants in Tübingen",
        "Traditional swabian food and drinks. Restaurants serve local food "
        "like maultaschen. Many cafes and bars offer drinks until late.",
    ),
    (
        "https://site-b.test/wine-bars",
        "Wine bars",
        "Wine bars and pubs serve drinks in the old town. Food trucks gather "
        "near the market during summer.",
    ),
    (
        "https://site-b.test/market",
        "Weekly market",
        "The weekly market sells fresh food, vegetables and flowers on the "
        "market square in front of the town hall.",
    ),
    (
        "https://site-c.test/university",
        "University of Tübingen",
        "The university was founded in 1477. Students from many countries "
        "study at the university today.",
    ),
    (
        "https://site-c.test/punting",
        "Punting boats",
        "Punting boats float on the river Neckar. A boat tour on the river "
        "is a popular attraction in summer.",
    ),
    (
        "https://site-c.test/attractions",
        "Top attractions",
        "Top attractions include the castle, the weekly market and punting "
        "on the river.",
    ),
]


def write_corpus(data_dir) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for number, (url, title, text) in enumerate(CORPUS):
        host_dir = data_dir / f"host{number % 3}"
        host_dir.mkdir(exist_ok=True)
        path = host_dir / f"doc{number}.html"
        path.write_text(
            f"<html><head><title>{title}</title></head>"
            f"<body><p>{text}</p></body></html>",
            encoding="utf-8",
        )
        records.append(
            {"url": url, "path": str(path), "title": title, "description": ""}
        )

    with (data_dir / "pages.jsonl").open("w", encoding="utf-8") as catalog:
        for record in records:
            catalog.write(json.dumps(record, ensure_ascii=False) + "\n")


@pytest.fixture(scope="session")
def index_path(tmp_path_factory) -> str:
    data_dir = tmp_path_factory.mktemp("crawl")
    write_corpus(data_dir)
    output = tmp_path_factory.mktemp("index") / "index.bin"
    index(str(data_dir), str(output))
    return str(output)
