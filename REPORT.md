# Tübingen Search — Project Report (Draft)

> Draft for the 4-page PDF report (INFO4271 Modern Search Engines, SoSe 2026).
> TODO before submission: add team member names, the frozen repository link
> (branch `submission`), UI screenshots, and the corpus/evaluation numbers
> from the final crawl. Convert to PDF (e.g. pandoc or Typst/LaTeX).

## 1. Introduction

We built a complete search engine for English web content about Tübingen:
a focused crawler, a self-implemented BM25 index, a multi-stage ranking
pipeline (RM3 pseudo-relevance feedback, LSA semantic re-ranking, MMR
diversification) and an explainable web interface. The system is implemented
entirely in Python; we deliberately avoid crawling/search toolkits and
pretrained retrieval models. [Repository link here.]

## 2. Crawling and Indexing (Component 1)

**Focused crawling.** The crawler maintains a single priority frontier across
domains. Outgoing links are scored by topical evidence before they are
fetched: mentions of "Tübingen" (all spelling variants) in the URL, English
path markers (`/en/`, `en.` subdomains), seed-host membership, and a shallow
path bonus. This best-first strategy keeps the crawl close to relevant
content instead of breadth-first drifting.

**Storing only relevant English pages.** A fetched page is stored only if it
is (a) about Tübingen — mention in URL/title, or ≥3 mentions in the text —
and (b) English. Language identification is a deliberately simple,
self-implemented classifier that compares English vs. German function-word
ratios, with the HTML `lang` attribute as a tie-breaker; on our validation
sample it separates the two languages reliably while adding no dependencies.
Off-topic pages are dead ends (their links are not expanded); relevant German
pages are not stored, but their links are followed, because German sites about
Tübingen frequently link to their English versions.

**Politeness & robustness.** robots.txt is honored per host (cached parser,
crawl-delay respected up to 15 s), with ≥1 s between requests to the same
host. Redirect targets are re-canonicalized and de-duplicated. URLs are
normalized (lowercased host, fragments/queries stripped — this also avoids
session-ID and calendar traps); media/binary extensions and social-media
hosts are pruned. A per-host page cap keeps the corpus diverse and a fetch
budget bounds the crawl.

**Resumability.** Frontier, seen-set, per-host counters and statistics are
persisted atomically every 25 pages and on shutdown (including Ctrl+C);
stored documents are appended incrementally to `pages.jsonl`. Re-running the
same command resumes the crawl exactly where it stopped.

**Indexing.** Documents are parsed with a boilerplate-aware extractor
(navigation, headers, footers, forms and scripts are skipped; content tags
like `p`, `li`, `h1–h4` are kept). Terms are lowercased, stopword-filtered
and Porter-stemmed. The inverted index stores raw term frequencies and
document lengths so that BM25 parameters remain tunable at query time; title
terms are up-weighted (×3) as a weighted zone. The index is serialized with
msgpack; LSA matrices (Section 3) are stored alongside as compressed numpy
arrays. [Corpus statistics here: #pages, #hosts, #terms, index size.]

## 3. Query Processing (Component 2)

Our first stage is classical, self-implemented **Okapi BM25**
(k1 = 1.2, b = 0.75) over the stemmed index. On top of it we add three
retrieval innovations:

**RM3 pseudo-relevance feedback.** From the top 10 BM25 documents we
estimate a relevance model P(t|R) (score-weighted term distributions) and
interpolate it with the original query, w(t) = α·P(t|q) + (1−α)·P(t|RM) with
α = 0.6 and 10 expansion terms. BM25 is re-run with the weighted expanded
query. This addresses vocabulary mismatch for short queries such as "food
and drinks" (expanding towards *restaurant*, *café*, *swabian*, …).

**LSA semantic re-ranking.** We train latent semantic analysis on our own
corpus: a tf-idf matrix (log-tf, document-frequency bounds 3 ≤ df ≤ 0.5·N,
≤50k terms) is decomposed with truncated SVD into 192 dimensions. At query
time the query is projected into the latent space and the cosine similarity
to each candidate document is blended with the normalized BM25 score
(75% BM25 / 25% semantic) over a 300-document candidate pool. This satisfies
the "second stage on top of a classical first stage" requirement without any
pretrained (retrieval) model — the embeddings come from our corpus alone.

**Term-proximity re-ranking.** BM25 is a bag-of-words model: a page that
mentions "food" in the header and "drinks" in the footer scores like one
about *food and drinks*. For multi-term queries we therefore compute, per
candidate, the smallest token window covering all distinct query terms
(linear-time sliding window over term occurrences) and turn it into a score
|q| / window ∈ [0, 1] (1.0 when the terms are adjacent, 0 when a term is
missing). The score is blended into the ranking with weight 0.15. This is a
deliberately simple, fully self-implemented re-ranker that approximates
phrase matching without storing positional postings.

**MMR diversification.** Because graded relevance is pooled over many result
lists, near-duplicate pages (e.g. menu variants of the same site) waste rank
positions. Greedy maximal marginal relevance over the LSA vectors (λ = 0.85)
mildly demotes redundant results.

Queries can be issued interactively (UI/CLI) or in batch mode
(`tuebingen-search batch`), which produces the required
`query \t rank \t URL \t score` file with 100 results per query; a full
batch run takes well under a second per query, far below the 1-minute limit.

## 4. Search Result Presentation (Component 3)

The web UI (FastAPI + a dependency-free single-page frontend) goes beyond
ten blue links with three innovations:

1. **Explainable ranking.** Each result shows a score bar splitting its rank
   into BM25 vs. semantic contribution and chips with the matched (stemmed)
   terms — searchers can see *why* a result ranks where it does.
2. **Site facets.** A sidebar aggregates the result list by host; one click
   filters to a site, another removes the filter.
3. **Related searches from feedback.** The RM3 expansion terms (mapped back
   to readable surface forms) are offered as one-click query refinements,
   exposing the feedback loop to the user.

4. **Spotlight desktop app.** Beyond the browser, the same engine ships as a
   macOS-Spotlight-style desktop window (frameless, translucent, fully
   keyboard-driven: type-to-search with ~130 ms debounce, ↑/↓ to navigate,
   ↩ to open, esc to dismiss). The list presents a *Top Hit* plus further
   results; a preview pane shows the highlighted snippet and the per-result
   score decomposition (BM25 / semantic / proximity bars). The window is a
   thin `pywebview` shell around the same FastAPI endpoint — no second
   retrieval code path.

Snippets are query-dependent: the system selects the text window with the
best coverage/density of query terms and highlights matches, including
inflected forms via stemming. The CLI offers the same search with ANSI
highlighting, so the system remains usable without a browser.
[Screenshots here.]

## 5. Evaluation

[Report nDCG-oriented sanity checks on the two engineering queries here:
e.g. top-10 manual relevance, effect of ablations (BM25 only vs. +RM3 vs.
+LSA vs. +proximity vs. +MMR — the CLI exposes `--no-*` flags for exactly
this), and query latency / index size figures.]

## 6. Design Choices & Justification (summary)

- **No crawl/search frameworks** (per rules): crawler on `httpx` +
  `html.parser`; index, BM25, RM3, snippets, MMR implemented from scratch;
  `scikit-learn`/`scipy`/`numpy` only for the SVD; `nltk` only for the
  Porter stemmer.
- **Raw tf in the index** instead of precomputed scores keeps ranking
  parameters tunable without re-indexing.
- **Corpus-trained LSA** instead of pretrained embeddings: rule-compliant,
  tiny (≈ MBs), fast (vectorized numpy), and adapted to the domain
  vocabulary of Tübingen pages.
- **Conservative URL canonicalization** (drop queries/fragments) trades a
  small amount of recall for strong crawler-trap protection.

## 7. Work distribution

[Name: crawler — Name: indexing/ranking — Name: UI/API — Name: evaluation.]
