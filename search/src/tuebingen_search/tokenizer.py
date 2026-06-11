"""Tokenization and term analysis (stopword removal + Porter stemming)."""

from __future__ import annotations

import re
from functools import lru_cache

from nltk.stem import PorterStemmer

TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)

# Compact English stopword list; kept inline so no corpus download is needed.
STOPWORDS = frozenset("""
a about above after again against all am an and any are as at be because been
before being below between both but by can cannot could did do does doing down
during each few for from further had has have having he her here hers herself
him himself his how i if in into is it its itself just me more most my myself
no nor not now of off on once only or other our ours ourselves out over own
same she should so some such than that the their theirs them themselves then
there these they this those through to too under until up very was we were
what when where which while who whom why will with would you your yours
yourself yourselves
""".split())

_stemmer = PorterStemmer()


def tokenize(text: str) -> list[str]:
    """Lowercased alphanumeric tokens of length >= 2."""
    return [token for token in TOKEN_PATTERN.findall(text.lower()) if len(token) >= 2]


def tokenize_with_offsets(text: str) -> list[tuple[str, int, int]]:
    """Like tokenize(), but with (token, start, end) character offsets."""
    return [
        (match.group().lower(), match.start(), match.end())
        for match in TOKEN_PATTERN.finditer(text)
        if len(match.group()) >= 2
    ]


@lru_cache(maxsize=100_000)
def stem(token: str) -> str:
    return _stemmer.stem(token)


def analyze(text: str) -> list[str]:
    """Index/query terms: tokenized, stopwords removed, Porter-stemmed."""
    return [stem(token) for token in tokenize(text) if token not in STOPWORDS]
