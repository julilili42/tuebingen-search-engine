# Crawl

Focused crawler for English, Tübingen-related web pages. It fetches HTML pages,
scores pages and links with the `verdict-ml` PageVerdict/LinkVerdict models,
drops near-duplicates via SimHash, respects `robots.txt`, and persists crawl
state so interrupted runs can resume.

## Setup

```bash
uv sync
```

Run commands from the repository root.

## Usage

```bash
uv run crawl
uv run crawl report --db data/pages.sqlite
```

- Seeds live in `crawl/seeds.toml`.
- Each `[[sites]]` entry supports `url`, `request_delay`, optional
  `max_pages_per_seed`, and optional `round_robin_weight` (default `1`).
- Seeds are crawled with weighted round-robin scheduling, so no single seed
  frontier monopolizes the crawl. Higher `round_robin_weight` gives a seed more
  pages per scheduler round.
- HTML is saved under `data/<host>/`; per-seed state is saved under
  `data/state/`; page and link metadata is recorded in `data/pages.sqlite`.
- Saved pages are capped per host, and hosts with repeated rejects and no saved
  pages are stopped early.

## Stored Metadata

PageVerdict fields are stored for saved and rejected pages:

```text
pageverdict_score
pageverdict_label
pageverdict_decision
pageverdict_model
pageverdict_snippet
```

Link candidates are stored with parent page context, anchor/target metadata,
LinkVerdict score/label/model, enqueue/selection decisions, rejection reasons,
and target page outcome metadata (`target_status`, target PageVerdict fields,
target rejection reason, etc.).

## Training Exports

Crawler exports are available through `CrawlExportDB` in
`tuebingen_crawler.save_pages` and are covered by tests. The `verdict-ml`
training commands consume the labeling database and crawl outcome data:

```bash
uv run verdict-ml-train-page
uv run verdict-ml-train-link --crawl-db data/pages.sqlite
```

Model artifacts are expected under `verdict-ml/artifacts/`.
