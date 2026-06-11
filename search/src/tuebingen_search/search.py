"""Two-stage retrieval: BM25 (+ RM3 feedback) and LSA semantic re-ranking.

Pipeline for a query:

1. BM25 over the inverted index (classical first stage, implemented here).
2. RM3 pseudo-relevance feedback: expansion terms are estimated from the
   top-ranked documents and BM25 is re-run with the expanded weighted query.
3. Semantic re-ranking: candidate scores are blended with the cosine
   similarity between query and document in the corpus-trained LSA space.
4. Term proximity: for multi-term queries, documents where the query terms
   occur close together (smallest token window covering all terms) receive
   a boost over documents that merely mention them far apart.
5. MMR diversification mildly demotes near-duplicate results.
"""

from __future__ import annotations

import bisect
import logging
import math
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import msgpack
import numpy as np

from .snippets import best_snippet
from .tokenizer import STOPWORDS, analyze, stem, tokenize

logger = logging.getLogger(__name__)

BM25_K1 = 1.2
BM25_B = 0.75

RM3_FEEDBACK_DOCS = 10
RM3_FEEDBACK_TERMS = 10
RM3_ORIGINAL_WEIGHT = 0.6

CANDIDATE_POOL = 300
SEMANTIC_BLEND = 0.25
PROXIMITY_BLEND = 0.15
MMR_LAMBDA = 0.85

# Instant search: the last, possibly unfinished query token is expanded to
# the most frequent index terms it could complete to ("tübin" → "tübingen").
PREFIX_MAX_COMPLETIONS = 5
PREFIX_MIN_STEM_LENGTH = 4


@dataclass(frozen=True)
class SearchResult:
    rank: int
    score: float
    url: str
    title: str
    host: str
    snippet: str
    highlights: list[tuple[int, int]]
    bm25_score: float
    semantic_score: float
    proximity_score: float
    matched_terms: list[str]


@dataclass(frozen=True)
class RetrievalResponse:
    results: list[SearchResult]
    query_terms: list[str]
    expansion_terms: list[str] = field(default_factory=list)
    completions: list[str] = field(default_factory=list)
    total_matches: int = 0


class SearchEngine:
    """Loads a serialized index once and answers queries from memory."""

    def __init__(self, index_path: str) -> None:
        start = time.perf_counter()
        with Path(index_path).open("rb") as index_file:
            raw = msgpack.unpack(index_file, raw=False)

        self.documents: list[list] = raw["documents"]  # [url, title, length, text]
        self.postings: dict[str, list[int]] = raw["postings"]
        self.avg_doc_length: float = raw["avg_doc_length"] or 1.0
        self.doc_count = len(self.documents)

        vectors_path = Path(index_path + ".npz")
        if vectors_path.exists():
            vectors = np.load(vectors_path)
            self.doc_vectors: np.ndarray = vectors["doc_vectors"]
            self.term_vectors: np.ndarray = vectors["term_vectors"]
        else:
            self.doc_vectors = np.zeros((self.doc_count, 0), dtype=np.float32)
            self.term_vectors = np.zeros((0, 0), dtype=np.float32)

        self.lsa_term_ids = {term: i for i, term in enumerate(raw.get("lsa_vocab", []))}
        self._sorted_terms = sorted(self.postings)
        self.idf = {
            term: math.log(
                (self.doc_count - df + 0.5) / (df + 0.5) + 1.0
            )
            for term, df in (
                (term, len(plist) // 2) for term, plist in self.postings.items()
            )
        }
        logger.info(
            "Loaded %s: %d documents, %d terms in %.2fs",
            index_path, self.doc_count, len(self.postings), time.perf_counter() - start,
        )

    @property
    def semantic_enabled(self) -> bool:
        return self.doc_vectors.shape[1] > 0

    def retrieve(
        self,
        query: str,
        top_n: int = 100,
        use_rm3: bool = True,
        use_semantic: bool = True,
        use_proximity: bool = True,
        use_mmr: bool = True,
        use_prefix: bool = True,
    ) -> RetrievalResponse:
        start = time.perf_counter()
        query_terms = analyze(query)
        base_weights = {term: 1.0 for term in query_terms}

        completion_stems: list[str] = []
        if use_prefix:
            raw_tokens = tokenize(query)
            if raw_tokens and raw_tokens[-1] not in STOPWORDS:
                for term, weight in self._prefix_completions(raw_tokens[-1]).items():
                    if term not in base_weights:
                        base_weights[term] = weight
                        completion_stems.append(term)

        if not base_weights:
            return RetrievalResponse(results=[], query_terms=query_terms)

        scores = self._bm25(base_weights)
        if not scores:
            return RetrievalResponse(
                results=[], query_terms=query_terms, completions=completion_stems
            )

        expansion_terms: list[str] = []
        expansion_stems: list[str] = []
        if use_rm3:
            term_weights, expansion_terms = self._rm3_weights(base_weights, scores)
            expansion_stems = [
                term for term in term_weights if term not in base_weights
            ]
            if expansion_stems:
                scores = self._bm25(term_weights)

        candidate_ids = sorted(scores, key=scores.__getitem__, reverse=True)
        candidate_ids = candidate_ids[:CANDIDATE_POOL]

        bm25_scores = np.array([scores[doc_id] for doc_id in candidate_ids])
        normalized_bm25 = _min_max(bm25_scores)

        semantic = np.zeros(len(candidate_ids))
        final = normalized_bm25
        query_vector = (
            self._query_vector(list(base_weights)) if use_semantic else None
        )
        if query_vector is not None:
            cosines = self.doc_vectors[candidate_ids] @ query_vector
            semantic = np.clip(cosines, 0.0, 1.0)
            final = (1.0 - SEMANTIC_BLEND) * normalized_bm25 + SEMANTIC_BLEND * semantic

        proximity = np.zeros(len(candidate_ids))
        unique_stems = frozenset(query_terms)
        if use_proximity and len(unique_stems) >= 2:
            proximity = np.array(
                [self._proximity(doc_id, unique_stems) for doc_id in candidate_ids]
            )
            final = (1.0 - PROXIMITY_BLEND) * final + PROXIMITY_BLEND * proximity

        order = (
            self._mmr_order(candidate_ids, final, top_n)
            if use_mmr and self.semantic_enabled
            else np.argsort(-final)[:top_n]
        )

        all_terms = query_terms + completion_stems + expansion_stems
        query_stems = set(query_terms) | set(completion_stems)
        results = []
        for rank, candidate_index in enumerate(order, start=1):
            doc_id = candidate_ids[candidate_index]
            url, title, _length, text = self.documents[doc_id]
            snippet, highlights = best_snippet(text, query_stems)
            results.append(
                SearchResult(
                    rank=rank,
                    score=round(float(final[candidate_index]), 4),
                    url=url,
                    title=title or url,
                    host=urlparse(url).hostname or "",
                    snippet=snippet,
                    highlights=highlights,
                    bm25_score=round(float(normalized_bm25[candidate_index]), 4),
                    semantic_score=round(float(semantic[candidate_index]), 4),
                    proximity_score=round(float(proximity[candidate_index]), 4),
                    matched_terms=self._matched_terms(doc_id, all_terms),
                )
            )

        logger.info(
            "Query %r: %d matches in %.3fs", query, len(scores), time.perf_counter() - start
        )
        return RetrievalResponse(
            results=results,
            query_terms=query_terms,
            expansion_terms=expansion_terms,
            completions=completion_stems,
            total_matches=len(scores),
        )

    # ------------------------------------------------------------------
    # Stage 1: BM25
    # ------------------------------------------------------------------

    def _bm25(self, term_weights: dict[str, float]) -> dict[int, float]:
        """Okapi BM25 with per-term query weights (uniform without RM3)."""
        scores: dict[int, float] = {}
        for term, weight in term_weights.items():
            plist = self.postings.get(term)
            if plist is None:
                continue
            idf = self.idf[term]
            for i in range(0, len(plist), 2):
                doc_id, term_frequency = plist[i], plist[i + 1]
                doc_length = self.documents[doc_id][2]
                normalizer = term_frequency + BM25_K1 * (
                    1.0 - BM25_B + BM25_B * doc_length / self.avg_doc_length
                )
                contribution = idf * term_frequency * (BM25_K1 + 1.0) / normalizer
                scores[doc_id] = scores.get(doc_id, 0.0) + weight * contribution
        return scores

    # ------------------------------------------------------------------
    # Instant search: prefix completion of the last query token
    # ------------------------------------------------------------------

    def _prefix_completions(self, token: str) -> dict[str, float]:
        """Index terms the (possibly unfinished) token could complete to,
        weighted by their share of document frequency among the candidates.

        Two directions are checked against the stemmed vocabulary: terms the
        typed prefix extends to ("tübin" → "tübingen"), and terms the typed
        text already extends past, because stems are often shorter than the
        typed surface form ("attracti" → "attract")."""
        candidates: set[str] = set()

        index = bisect.bisect_left(self._sorted_terms, token)
        while index < len(self._sorted_terms) and len(candidates) < 50:
            term = self._sorted_terms[index]
            if not term.startswith(token):
                break
            candidates.add(term)
            index += 1

        for length in range(PREFIX_MIN_STEM_LENGTH, len(token)):
            if token[:length] in self.postings:
                candidates.add(token[:length])

        ranked = sorted(candidates, key=self._document_frequency, reverse=True)
        ranked = ranked[:PREFIX_MAX_COMPLETIONS]

        total = sum(self._document_frequency(term) for term in ranked)
        if total == 0:
            return {}
        return {
            term: self._document_frequency(term) / total for term in ranked
        }

    def _document_frequency(self, term: str) -> int:
        return len(self.postings.get(term, ())) // 2

    # ------------------------------------------------------------------
    # Stage 2a: RM3 pseudo-relevance feedback
    # ------------------------------------------------------------------

    def _rm3_weights(
        self, base_weights: dict[str, float], scores: dict[int, float]
    ) -> tuple[dict[str, float], list[str]]:
        """Interpolate the original query with a relevance model estimated
        from the top-ranked documents: w(t) = a*P(t|q) + (1-a)*P(t|RM).

        Returns the stemmed term weights for scoring and the expansion terms
        as display-friendly surface forms (most frequent unstemmed token).
        """
        feedback_ids = sorted(scores, key=scores.__getitem__, reverse=True)
        feedback_ids = feedback_ids[:RM3_FEEDBACK_DOCS]

        total_score = sum(scores[doc_id] for doc_id in feedback_ids)
        if total_score <= 0.0:
            return dict(base_weights), []

        relevance_model: Counter[str] = Counter()
        surface_forms: Counter[tuple[str, str]] = Counter()
        for doc_id in feedback_ids:
            doc_weight = scores[doc_id] / total_score
            stemmed_pairs = [
                (stem(token), token)
                for token in tokenize(self.documents[doc_id][3])
                if token not in STOPWORDS
            ]
            if not stemmed_pairs:
                continue
            surface_forms.update(stemmed_pairs)
            terms = [stemmed for stemmed, _ in stemmed_pairs]
            counts = Counter(terms)
            for term, term_frequency in counts.items():
                relevance_model[term] += doc_weight * term_frequency / len(terms)

        query_set = set(base_weights)
        expansion = [
            (term, probability)
            for term, probability in relevance_model.most_common()
            if term not in query_set and len(term) >= 3 and term.isalpha()
        ][:RM3_FEEDBACK_TERMS]

        probability_mass = sum(probability for _, probability in expansion)
        base_mass = sum(base_weights.values())
        weights = {
            term: RM3_ORIGINAL_WEIGHT * weight / base_mass
            for term, weight in base_weights.items()
        }
        if probability_mass > 0.0:
            for term, probability in expansion:
                weights[term] = (
                    (1.0 - RM3_ORIGINAL_WEIGHT) * probability / probability_mass
                )

        display_terms = [
            _most_common_surface(surface_forms, term) for term, _ in expansion
        ]
        return weights, display_terms

    # ------------------------------------------------------------------
    # Stage 2b: LSA semantic similarity
    # ------------------------------------------------------------------

    def _query_vector(self, query_terms: list[str]) -> np.ndarray | None:
        if not self.semantic_enabled:
            return None
        rows = [
            self.lsa_term_ids[term] for term in query_terms if term in self.lsa_term_ids
        ]
        if not rows:
            return None
        vector = self.term_vectors[rows].sum(axis=0)
        norm = np.linalg.norm(vector)
        return vector / norm if norm > 0.0 else None

    # ------------------------------------------------------------------
    # Stage 2c: term proximity
    # ------------------------------------------------------------------

    def _proximity(self, doc_id: int, query_stems: frozenset[str]) -> float:
        """Score in [0, 1]: 1.0 when all query terms are adjacent, decaying
        with the smallest token window that covers every distinct term, and
        0.0 when the stored text does not contain all of them."""
        occurrences = [
            (position, stemmed)
            for position, token in enumerate(tokenize(self.documents[doc_id][3]))
            if (stemmed := stem(token)) in query_stems
        ]
        if len({stemmed for _, stemmed in occurrences}) < len(query_stems):
            return 0.0

        # Sliding window over the occurrence list: smallest span of token
        # positions that contains every distinct query stem.
        best_span = math.inf
        window_counts: Counter[str] = Counter()
        left = 0
        for right, (right_position, right_stem) in enumerate(occurrences):
            window_counts[right_stem] += 1
            while len(window_counts) == len(query_stems):
                left_position, left_stem = occurrences[left]
                best_span = min(best_span, right_position - left_position + 1)
                window_counts[left_stem] -= 1
                if window_counts[left_stem] == 0:
                    del window_counts[left_stem]
                left += 1

        return len(query_stems) / best_span

    # ------------------------------------------------------------------
    # Stage 3: MMR diversification
    # ------------------------------------------------------------------

    def _mmr_order(
        self, candidate_ids: list[int], final_scores: np.ndarray, top_n: int
    ) -> list[int]:
        """Greedy maximal marginal relevance over the LSA vectors."""
        vectors = self.doc_vectors[candidate_ids]
        remaining = list(np.argsort(-final_scores))
        selected: list[int] = []
        max_similarity = np.zeros(len(candidate_ids))

        while remaining and len(selected) < top_n:
            best_index = max(
                remaining,
                key=lambda i: MMR_LAMBDA * final_scores[i]
                - (1.0 - MMR_LAMBDA) * max_similarity[i],
            )
            remaining.remove(best_index)
            selected.append(best_index)

            similarity = np.clip(vectors @ vectors[best_index], 0.0, 1.0)
            max_similarity = np.maximum(max_similarity, similarity)
        return selected

    # ------------------------------------------------------------------

    def _matched_terms(self, doc_id: int, terms: list[str]) -> list[str]:
        matched = []
        for term in terms:
            plist = self.postings.get(term)
            if plist is None:
                continue
            doc_ids = plist[::2]
            position = bisect.bisect_left(doc_ids, doc_id)
            if position < len(doc_ids) and doc_ids[position] == doc_id:
                matched.append(term)
        return matched

    def suggest_queries(self, query: str, expansion_terms: list[str]) -> list[str]:
        """Related-search suggestions built from RM3 expansion terms."""
        base = " ".join(tokenize(query))
        return [f"{base} {term}" for term in expansion_terms[:5]]


def _most_common_surface(
    surface_forms: Counter[tuple[str, str]], term: str
) -> str:
    candidates = [
        (count, surface)
        for (stemmed, surface), count in surface_forms.items()
        if stemmed == term
    ]
    return max(candidates)[1] if candidates else term


def _min_max(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    low, high = float(values.min()), float(values.max())
    if high - low < 1e-12:
        return np.ones_like(values)
    return (values - low) / (high - low)


def retrieve(query: str, index_path: str, top_n: int = 100) -> RetrievalResponse:
    """Convenience wrapper matching the project skeleton's signature."""
    return SearchEngine(index_path).retrieve(query, top_n=top_n)
