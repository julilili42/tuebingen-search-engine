# Labeling

Standalone labeling UI for collecting relevance training data for crawler
verdicts and later search ranking experiments.

The UI stores its own data in `labeling/data/labeling.sqlite`. The optional
crawler export commands read the crawl database through the `crawler` workspace
package and emit CSVs that can be imported into the labeling UI.

Configure Serper:

```bash
export SERPER_API_KEY="..."
```

Run from the project root:

```bash
uv run tuebingen-labeling
```

Then open:

```text
http://127.0.0.1:8010
```

Serper workflow:

```text
query -> Serper result pages 1-4 -> title/url/snippet -> rating 1-5
```

Crawler candidate relabeling workflows:

```bash
uv run tuebingen-export-pageverdict
uv run tuebingen-export-link-candidates
uv run tuebingen-labeling
```

Then use the Candidate CSV import controls in the UI with:

- `data/pageverdict_candidates.csv` for fresh crawler decisions
- `data/pageverdict_error_candidates.csv` for PageVerdict validation errors and boundary cases
- `data/link_candidates.csv` in `Links` mode for link-follow decisions

Imported candidates are stored in the same `serp_results` table and are sorted
by model uncertainty first, with validation errors shown before boundary cases.
Link candidates are stored separately in `link_results` and can be exported at
`http://127.0.0.1:8010/api/export/link-labels.csv`.

Starter queries:

- `labeling/queries/tuebingen_serp_queries.txt`

Rating convention:

- `1`: reject
- `2`: bad
- `3`: unsure
- `4`: good
- `5`: great

The API maps `1-2` to `negative`, `3` to `skip`, and `4-5` to `positive`.

CSV exports:

- `http://127.0.0.1:8010/api/export/serp-labels.csv`
- `http://127.0.0.1:8010/api/export/link-labels.csv`
