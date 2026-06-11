"""Search engine for English web content about Tübingen.

Two-stage retrieval: self-implemented BM25 with RM3 pseudo-relevance
feedback, re-ranked with corpus-trained LSA embeddings and MMR.
"""

from .batch import batch
from .indexer import index
from .search import RetrievalResponse, SearchEngine, SearchResult, retrieve

__all__ = [
    "RetrievalResponse",
    "SearchEngine",
    "SearchResult",
    "batch",
    "index",
    "retrieve",
]
