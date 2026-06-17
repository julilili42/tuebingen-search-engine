# Crawl

Link crawler that discovers English, Tübingen-related web pages and stores them
locally. It respects `robots.txt` and is resumable: re-running picks up where a
previous run stopped.

## Setup

```bash
uv sync
```

(Workspace member — run from the repo root.)

## Usage

```bash
uv run tuebingen-crawl
```

- Seeds are configured in `crawl/seeds.toml` — one `[[sites]]` entry per seed
  with `url`, `max_pages`, and `request_delay`.
- HTML is saved under `data/<host>/`; page metadata is recorded in
  `data/pages.sqlite`.
- Crawl state is persisted per host, so an interrupted crawl resumes on the next
  run.
