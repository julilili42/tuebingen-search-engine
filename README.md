# Tübingen Search Engine

A search engine for **English web content about Tübingen**, built for the
INFO4271 *Modern Search Engines* group project. Everything is implemented in
Python: a polite, resumable, topic-focused web crawler; a self-implemented
BM25 index; RM3 pseudo-relevance feedback; LSA semantic re-ranking trained on
our own corpus; and a web UI with an explainable, faceted result view.

## Architecture

```
crawl/   tuebingen_crawler   focused crawler  →  data/crawl/{pages.jsonl, <host>/*.html}
search/  tuebingen_search    indexer + retrieval + CLI + API/UI  →  index.bin (+ .npz)
```

### Retrieval pipeline (per query)

1. **BM25** (self-implemented, k1=1.2, b=0.75, weighted title zone) over a
   stemmed, stopword-filtered inverted index — the classical first stage.
2. **RM3 pseudo-relevance feedback**: a relevance model is estimated from the
   top 10 documents and interpolated with the original query (α=0.6); BM25 is
   re-run with the expanded weighted query.
3. **LSA semantic re-ranking**: cosine similarity between query and document
   in a 192-dimensional latent space (TruncatedSVD over our own tf-idf
   matrix — no pretrained retrieval models), blended with the BM25 score.
4. **Term-proximity re-ranking**: for multi-term queries, documents where all
   query terms occur close together (smallest covering token window) are
   boosted over documents that mention them far apart.
5. **MMR diversification** (λ=0.85) mildly demotes near-duplicate results.

## Setup

Requires [uv](https://docs.astral.sh/uv/). Install everything with:

```bash
uv sync --all-packages
```

## Usage

### 1. Crawl

```bash
uv run tuebingen-crawl -n 5000 -d data/crawl
```

Starts from a built-in seed list of English pages about Tübingen (override
with `--seeds seeds.txt`). The crawler respects robots.txt and crawl delays,
keeps at most one request per second per host, follows links across domains
ordered by a Tübingen-relevance priority, and only stores pages that are
**English** (function-word language detection) and **about Tübingen**.
It can be interrupted at any time (Ctrl+C) and resumes from its saved state;
re-run the same command to continue.

| Flag | Default | Description |
|------|---------|-------------|
| `-s, --seeds` | built-in list | File with one seed URL per line |
| `-d, --save-dir` | `data/crawl` | Output directory (HTML, `pages.jsonl`, state) |
| `-n, --max-pages` | `5000` | Stop after this many stored pages |
| `--max-pages-per-host` | `800` | Per-host cap, keeps the corpus diverse |
| `--host-delay` | `1.0` | Minimum seconds between requests per host |

### 2. Build the index

```bash
uv run tuebingen-search index -d data/crawl -o index.bin
```

Writes the BM25 index (`index.bin`) and the LSA matrices (`index.bin.npz`).

### 3. Search (CLI)

```bash
uv run tuebingen-search search -q "tübingen attractions" -t 10
```

Prints ranked results with highlighted query-dependent snippets, the
BM25/semantic/proximity score split, and the RM3 expansion terms.
`--no-rm3` / `--no-semantic` / `--no-proximity` switch off individual
pipeline stages (useful for ablation experiments).

### 4. Batch evaluation

```bash
uv run tuebingen-search batch -q queries.txt -o results.txt
```

`queries.txt` has one `<number>\t<query>` per line (see the committed example).
`results.txt` contains 100 results per query as
`<query#>\t<rank>\t<url>\t<score>` — the format required for evaluation.

### 5. Web UI

```bash
INDEX_PATH=index.bin uv run uvicorn tuebingen_search.api:app
```

Open http://127.0.0.1:8000/ — features beyond ten blue links:

- **Explainable ranking**: every result shows its score split into BM25
  (keyword) and LSA (semantic) contributions plus the matched terms.
- **Query-dependent snippets** with highlighted matches (including stemmed
  variants of the query words).
- **Site facets**: filter the result list by host with one click.
- **Related searches** generated from the RM3 relevance model.

API docs are at `/docs` (`GET /api/search?q=…&top_n=…&host=…`).

### 6. Spotlight desktop app

```bash
uv sync --all-packages --all-extras   # once, installs pywebview
uv run tuebingen-desktop -i index.bin
```

Opens a frameless, translucent **macOS-Spotlight-style window**: type to
search instantly, navigate with `↑`/`↓`, open the selected page with `↩`,
press `esc` to clear (and again to close). The list shows a *Top Hit*
followed by further results; the preview pane on the right shows the
highlighted snippet, the BM25/semantic/proximity score bars, matched terms
and related searches. The window serves the same FastAPI app and index as
the web UI — without pywebview installed, the same interface opens in the
browser (also reachable at `/spotlight`).

## Tests

```bash
uv run pytest crawl/tests search/tests
```

Covers URL normalization, language detection, relevance scoring, the
frontier, a mocked end-to-end crawl (including resuming), tokenization,
indexing, BM25/RM3/LSA retrieval, snippet generation, the batch format and
the HTTP API.
