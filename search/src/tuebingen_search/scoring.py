import math
from collections import Counter
from .models import Document, TermFrequency

def compute_tf(terms: list[str]) -> TermFrequency:
    return dict(Counter(terms))

# tf-idf
def compute_df(index: dict[Document, TermFrequency]) -> TermFrequency:
    df: Counter[str] = Counter()
    for tf in index.values():
        df.update(tf.keys())
    return dict(df)

def compute_idf(index: dict[Document, TermFrequency]) -> dict[str, float]:
    N = len(index)
    return {
        term: math.log((1.0 + N) / (1.0 + doc_freq)) + 1.0
        for term, doc_freq in compute_df(index).items()
    }

def compute_tf_idf(term_frequency: int, idf_score: float) -> float:
    score = term_frequency * idf_score
    return score

# bm25
def compute_bm25_idf(index: dict[Document, TermFrequency]) -> dict[str, float]:
    n_docs = len(index)
    return {
        term: math.log(1.0 + (n_docs - doc_freq + 0.5) / (doc_freq + 0.5))
        for term, doc_freq in compute_df(index).items()
    }

def compute_average_document_length(index: dict[Document, TermFrequency]) -> float:
    if not index:
        return 0.0

    return sum(document.length for document in index.keys()) / len(index)

def compute_bm25_score(
    *,
    term_frequency: int,
    idf_score: float,
    document_length: int,
    average_document_length: float,
    k1: float = 1.2,
    b: float = 0.75,
) -> float:
    if term_frequency <= 0 or average_document_length <= 0:
        return 0.0

    length_norm = 1.0 - b + b * (document_length / average_document_length)

    return idf_score * (
        (term_frequency * (k1 + 1.0))
        / (term_frequency + k1 * length_norm)
    )

