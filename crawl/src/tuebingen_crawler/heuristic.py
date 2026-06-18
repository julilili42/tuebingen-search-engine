from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

import nltk
from nltk.corpus import stopwords

from .urls import normalize_host

_STOPWORDS: tuple[set[str], set[str]] | None = None

TUEBINGEN_TERMS: dict[str, float] = {
    "tübingen": 3.0, "tuebingen": 3.0, "tubingen": 3.0,
    "neckar": 1.0, "swabia": 1.0, "schwaben": 1.0,
    "eberhard karls": 1.5, "hölderlin": 1.0, "hoelderlin": 1.0,
    "hohentübingen": 1.5, "bebenhausen": 1.0, "stiftskirche": 0.5,
}

# skip sites wich end in these suffixes
RESOURCE_SUFFIXES = (
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js",
    ".pdf", ".zip", ".mp4", ".mp3", ".ico", ".woff", ".woff2",
)

# language detection reliable if >= 30 tokens
MIN_TOKENS_FOR_LANG = 30
# site is relevant
REL_THRESHOLD = 3.0
# link is added to frontier
LINK_THRESHOLD = 3.0
# link is ignored
MAX_DEPTH = 5

# tuebingen terms in url and title weight
_TERM_IN_URL_WEIGHT = 5.0
_TERM_IN_TITLE_WEIGHT = 3.0

TOKEN_RE = re.compile(r"[a-zäöüß]+", re.IGNORECASE)

class Language(StrEnum):
    EN = "en"
    DE = "de"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class PageVerdict:
    language: Language
    relevance: float

    @property
    def keep(self) -> bool:
        return self.is_english and self.is_relevant

    @property
    def is_english(self) -> bool:
        return self.language is Language.EN

    @property
    def is_relevant(self) -> bool:
        return self.relevance >= REL_THRESHOLD

def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]

def check_nltk_stopwords() -> None:
    try:
        stopwords.words("english")
        stopwords.words("german")
    except LookupError:
        nltk.download("stopwords")

def load_stopwords() -> tuple[set[str], set[str]]:
    global _STOPWORDS

    if _STOPWORDS is None:
        check_nltk_stopwords()
        german_stopwords = set(stopwords.words("german"))
        english_stopwords = set(stopwords.words("english"))

        common = sorted(german_stopwords & english_stopwords)
        english_stopwords.difference_update(common)
        german_stopwords.difference_update(common)
        _STOPWORDS = german_stopwords, english_stopwords

    return _STOPWORDS

def _host(url: str) -> str:
    try:
        netloc = urlparse(url).hostname or ""
    except ValueError:
        return ""
    return normalize_host(netloc)

# POST FETCH
def detect_language(text: str, lang_attribute: str | None = None) -> Language:
    tokens = tokenize(text)

    if len(tokens) < MIN_TOKENS_FOR_LANG:
        if lang_attribute:
            return language_from_attribute(lang_attribute)
        return Language.UNKNOWN

    german_stopwords, english_stopwords = load_stopwords()
    en = sum(t in english_stopwords for t in tokens)
    de = sum(t in german_stopwords for t in tokens)

    if en >= 5 and en >= de:
        return Language.EN
    if de >= 5 and de >= en:
        return Language.DE

    # use <html lang="..."> as tiebreaker
    if lang_attribute:
        return language_from_attribute(lang_attribute)
    return Language.UNKNOWN

def language_from_attribute(lang_attribute: str) -> Language:
    lang = lang_attribute.lower()
    if lang.startswith("en"):
        return Language.EN
    if lang.startswith("de"):
        return Language.DE
    return Language.UNKNOWN

def relevance_score(url: str, title: str, text: str) -> float:
    url, title, text = url.lower(), title.lower(), text.lower()
    n_tokens = max(len(tokenize(text)), 1)

    score = 0.0
    for term, weight in TUEBINGEN_TERMS.items():
        # url and title significantly increase the score
        # if they contain terms related to tuebingen
        if term in url:
            score += weight * _TERM_IN_URL_WEIGHT
        if term in title:
            score += weight * _TERM_IN_TITLE_WEIGHT

        # TODO: Counts substrings not terms
        # calculate score based on term weight and term frequency in the body
        term_frequency = text.count(term)
        if term_frequency:
            score += weight * min(term_frequency / n_tokens * 1000.0, 5.0)
    return score

def evaluate_page(
    url: str,
    title: str,
    text: str,
    lang_attribute: str | None = None,
) -> PageVerdict:
    lang = detect_language(text, lang_attribute)
    rel = relevance_score(url, title, text)
    return PageVerdict(
        language=lang,
        relevance=rel,
    )

# PRE FETCH
LINK_FEATURE_WEIGHTS: dict[str, float] = {
    "anchor_has_tuebingen": 4.0,
    "url_has_tuebingen": 3.0,
    "parent_relevant": 2.0,
    "internal_link": 1.0,
}

def link_score(
    anchor: str,
    url: str,
    parent_relevance: float,
    parent_host: str,
) -> float:
    if url.lower().endswith(RESOURCE_SUFFIXES):
        return 0.0

    anchor_l, url_l = anchor.lower(), url.lower()
    features = {
        "anchor_has_tuebingen": any(t in anchor_l for t in TUEBINGEN_TERMS),
        "url_has_tuebingen": any(t in url_l for t in TUEBINGEN_TERMS),
        "parent_relevant": parent_relevance >= REL_THRESHOLD,
        "internal_link": _host(url) == normalize_host(parent_host),
    }
    return sum(w for name, w in LINK_FEATURE_WEIGHTS.items() if features[name])

def should_enqueue(
    score: float,
    depth: int,
    threshold: float = LINK_THRESHOLD,
    max_depth: int = MAX_DEPTH,
) -> bool:
    return score >= threshold and depth <= max_depth