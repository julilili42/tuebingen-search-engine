"""Index construction: BM25 inverted index + LSA document embeddings.

The index file (msgpack) stores document metadata, raw term frequencies and
the LSA vocabulary. Dense LSA matrices live in a sibling ``<index>.npz``.
"""

from __future__ import annotations

import json
import logging
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import msgpack
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD

from .html import extract_page, is_html_file
from .tokenizer import analyze

logger = logging.getLogger(__name__)

INDEX_VERSION = 2
# Title terms count this many times: a strong on-topic signal (weighted zone).
TITLE_WEIGHT = 3
# Characters of extracted text kept per document for snippet generation.
SNIPPET_TEXT_CHARS = 5000

LSA_DIMENSIONS = 192
LSA_MIN_DF = 3
LSA_MAX_DF_RATIO = 0.5
LSA_MAX_VOCABULARY = 50_000


@dataclass(frozen=True)
class CorpusDocument:
    url: str
    title: str
    text: str


def load_corpus(data_dir: str) -> list[CorpusDocument]:
    """Load crawled pages from ``pages.jsonl`` (crawler output).

    Falls back to scanning for ``*.html`` files when no catalog exists, so a
    plain directory of HTML files remains indexable.
    """
    directory = Path(data_dir)
    catalog = directory / "pages.jsonl"
    documents: list[CorpusDocument] = []
    seen_urls: set[str] = set()

    if catalog.exists():
        for line in catalog.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record["url"] in seen_urls:
                continue
            path = _resolve_record_path(directory, record["path"])
            if path is None:
                logger.warning("Missing HTML file for %s", record["url"])
                continue
            page = extract_page(path)
            seen_urls.add(record["url"])
            documents.append(
                CorpusDocument(
                    url=record["url"],
                    title=record.get("title") or page.title,
                    text=page.text,
                )
            )
        return documents

    logger.info("No pages.jsonl in %s; scanning for HTML files", directory)
    for path in sorted(directory.rglob("*.html")):
        if not is_html_file(path):
            continue
        page = extract_page(path)
        documents.append(CorpusDocument(url=str(path), title=page.title, text=page.text))
    return documents


def _resolve_record_path(data_dir: Path, recorded: str) -> Path | None:
    """Recorded paths depend on the crawler's working directory; try both the
    literal path and one re-anchored at the index data directory."""
    path = Path(recorded)
    if path.is_file():
        return path
    if len(path.parts) >= 2:
        reanchored = data_dir / Path(*path.parts[-2:])
        if reanchored.is_file():
            return reanchored
    return None


def build_index(documents: list[CorpusDocument], index_path: str) -> None:
    """Tokenize the corpus and write the BM25 index and LSA embeddings."""
    doc_meta: list[list] = []
    postings: dict[str, list[int]] = {}
    doc_term_counts: list[Counter[str]] = []
    total_length = 0

    for doc_id, document in enumerate(documents):
        text_terms = analyze(document.text)
        title_terms = analyze(document.title)

        counts = Counter(text_terms)
        for term in title_terms:
            counts[term] += TITLE_WEIGHT
        length = len(text_terms) + TITLE_WEIGHT * len(title_terms)

        for term, term_frequency in counts.items():
            postings.setdefault(term, []).extend((doc_id, term_frequency))

        doc_term_counts.append(counts)
        total_length += length
        doc_meta.append(
            [document.url, document.title, length, document.text[:SNIPPET_TEXT_CHARS]]
        )

    avg_doc_length = total_length / len(documents) if documents else 0.0
    lsa_vocab, doc_vectors, term_vectors = _build_lsa(doc_term_counts, postings)

    payload = {
        "version": INDEX_VERSION,
        "avg_doc_length": avg_doc_length,
        "documents": doc_meta,
        "postings": postings,
        "lsa_vocab": lsa_vocab,
    }
    path = Path(index_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as index_file:
        msgpack.pack(payload, index_file, use_bin_type=True)

    np.savez_compressed(
        _vectors_path(index_path), doc_vectors=doc_vectors, term_vectors=term_vectors
    )
    logger.info(
        "Indexed %d documents, %d terms, %d LSA dimensions",
        len(documents), len(postings), doc_vectors.shape[1] if doc_vectors.size else 0,
    )


def _vectors_path(index_path: str) -> str:
    return index_path + ".npz"


def _build_lsa(
    doc_term_counts: list[Counter[str]],
    postings: dict[str, list[int]],
) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Latent semantic analysis over the corpus' own tf-idf matrix.

    Returns (vocabulary, doc_vectors, term_vectors); empty arrays when the
    corpus is too small for a meaningful decomposition.
    """
    doc_count = len(doc_term_counts)
    document_frequency = {term: len(plist) // 2 for term, plist in postings.items()}

    vocabulary = [
        term
        for term, df in document_frequency.items()
        if LSA_MIN_DF <= df <= max(LSA_MAX_DF_RATIO * doc_count, LSA_MIN_DF)
    ]
    vocabulary.sort(key=lambda term: document_frequency[term], reverse=True)
    vocabulary = sorted(vocabulary[:LSA_MAX_VOCABULARY])

    dimensions = min(LSA_DIMENSIONS, len(vocabulary) - 1, doc_count - 1)
    if dimensions < 2:
        logger.info("Corpus too small for LSA; semantic re-ranking disabled")
        return [], np.zeros((doc_count, 0), dtype=np.float32), np.zeros((0, 0), dtype=np.float32)

    term_ids = {term: term_id for term_id, term in enumerate(vocabulary)}
    idf = {
        term: math.log(doc_count / document_frequency[term])
        for term in vocabulary
    }

    rows, cols, values = [], [], []
    for doc_id, counts in enumerate(doc_term_counts):
        for term, term_frequency in counts.items():
            term_id = term_ids.get(term)
            if term_id is not None:
                rows.append(doc_id)
                cols.append(term_id)
                values.append((1.0 + math.log(term_frequency)) * idf[term])

    matrix = csr_matrix(
        (values, (rows, cols)), shape=(doc_count, len(vocabulary)), dtype=np.float64
    )

    svd = TruncatedSVD(n_components=dimensions, random_state=42)
    doc_vectors = svd.fit_transform(matrix)
    term_vectors = svd.components_.T  # (vocabulary, dimensions)

    return (
        vocabulary,
        _normalize_rows(doc_vectors).astype(np.float32),
        term_vectors.astype(np.float32),
    )


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return matrix / norms


def index(data_dir: str, index_path: str) -> None:
    """Build the search index from a crawl directory."""
    logger.info("Loading corpus from %s ...", data_dir)
    documents = load_corpus(data_dir)
    if not documents:
        raise ValueError(f"no documents found in {data_dir}")

    logger.info("Building index for %d documents ...", len(documents))
    build_index(documents, index_path)
    logger.info("Saved %s", index_path)
