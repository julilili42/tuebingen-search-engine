# Search

Builds a BM25 inverted index over the crawled pages and serves retrieval through
a CLI and a FastAPI endpoint.

## Setup

```bash
uv sync
```

(Workspace member — run from the repo root.)

## Usage

Build the index from the crawled pages (`data/pages.sqlite` → `index.bin`):

```bash
uv run tuebingen-search index
```

Interactive single query:

```bash
uv run tuebingen-search search -q "tübingen attractions" -t 5
```

Batch run for evaluation:

```bash
uv run tuebingen-search batch -b queries.tsv -o results.tsv -t 100
```

Input — tab-separated, one query per line (`query-id`, `query text`):

```
1	tübingen attractions
2	food and drinks
```

Output — tab-separated, one ranked result per line (`query-id`, `rank`, `url`, `score`):

```
1	1	https://www.tuebingen.de/en/3521.html	0.7250
1	2	https://www.komoot.com/guide/355570/...	0.6710
```

HTTP API (`/search`, `/health`) used by the client:

```bash
uv run uvicorn tuebingen_search.api:app
```
