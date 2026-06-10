# Tübingen Search Engine

> A custom search engine with link crawling and an indexing pipeline.

## Usage

### 1. Crawl

```bash
uv run tuebingen-crawl
```

Crawls the sites configured in `crawl/src/tuebingen_crawler/main.py` and saves the HTML pages to `save_dir` (default `../data2`, one subfolder per host, relative to where you run the command).

### 2. Build the index

```bash
uv run tuebingen-search index -d ../data2 -o index.bin
```

| Flag | Default | Description |
|------|---------|-------------|
| `-d, --dir` | `../data2` | Directory with the crawled sites (one subfolder per host) |
| `-o, --output` | `index.bin` | Output path for the serialized index |

### 3. Search

```bash
uv run tuebingen-search search -q "boris palmer" -t 5
```

| Flag | Default | Description |
|------|---------|-------------|
| `-q, --query` | required | Search query |
| `-i, --index` | `index.bin` | Path to the index file |
| `-t, --top-n` | `10` | Number of results |

### Optional: HTTP API

```bash
INDEX_PATH=search/index.bin uv run uvicorn tuebingen_search.api:app
```

Then query `http://127.0.0.1:8000/search?q=boris+palmer&top_n=5` (interactive docs at `/docs`). `INDEX_PATH` defaults to `index.bin` in the current directory.
