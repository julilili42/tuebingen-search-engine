# Verdict ML

PageVerdict and LinkVerdict classifiers for the focused crawler.

Run commands from the repository root.

## Training

Train PageVerdict from manual page labels in `labeling/data/labeling.sqlite`:

```bash
uv run verdict-train page
```

Train LinkVerdict from manual link labels and crawl outcome labels:

```bash
uv run verdict-train link --crawl-db data/pages.sqlite
```

Use only manual link labels by omitting `--crawl-db`:

```bash
uv run verdict-train link
```

Artifacts are written to `verdict-ml/artifacts/`.

## Data Sources

- Page labels come from `serp_results` in the labeling DB.
- Link labels come from `link_results` in the labeling DB.
- Optional crawl outcome labels come from `link_candidates.target_status` in
  `data/pages.sqlite`.

Rating `3` is ignored. Ratings `1-2` train as `negative`; ratings `4-5` train
as `positive`.
