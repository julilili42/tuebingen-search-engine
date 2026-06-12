# Tübingen Search Engine

> A custom search engine with link crawling and an indexing pipeline.

## Usage

### 1. Crawl

```bash
uv run tuebingen-crawl
```

The URLs to crawl are defined in `crawl/seeds.toml` (one `[[sites]]` entry per seed, with `max_pages` and `request_delay`). Pages are saved as HTML to `save_dir` (default `../data`, one subfolder per host).

### 2. Build the index

```bash
uv run tuebingen-search index -d ../data2 -o index.bin
```

`-d` directory with the crawled sites, `-o` output path for the index.

### 3. Search

```bash
uv run tuebingen-search search -q "boris palmer" -t 5
```

`-q` query (required), `-i` index file (default `index.bin`), `-t` number of results (default 10).

### Optional: HTTP API

```bash
INDEX_PATH=search/index.bin uv run uvicorn tuebingen_search.api:app
```

Query `http://127.0.0.1:8000/search?q=boris+palmer&top_n=5` (docs at `/docs`).
