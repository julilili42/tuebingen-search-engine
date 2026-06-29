from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

import nltk
from nltk.corpus import stopwords

from .models import Language, REL_THRESHOLD
from .semantic import topic_similarity
from .tuebingen_terms import has_tuebingen, tuebingen_hits

_STOPWORDS: tuple[set[str], set[str]] | None = None

@dataclass(frozen=True)
class PageHeuristicsConfig:
    min_tokens: int = 30
    token_re: re.Pattern[str] = re.compile(r"[a-zäöüß]+", re.IGNORECASE)

@dataclass(frozen=True)
class SemanticScoringConfig:
    # Model similarity may demote lexical matches, but strong lexical pages stay visible.
    lexical_floor: float = 0.5
    # Admit clearly on-topic English pages even when they have no lexical signal.
    admit_threshold: float = 0.7
    admit_span: float = 2.0

@dataclass(frozen=True)
class LexicalScoringConfig:
    feature_weights: dict[str, float] = field(default_factory=lambda: {
        "url_has_tuebingen": 5.0,
        "title_has_tuebingen": 3.0,
        "description_has_tuebingen": 2.0,
        "h1_has_tuebingen": 3.0,
    })

HEURISTIC_CONFIG = PageHeuristicsConfig()
SEMANTIC_CONFIG = SemanticScoringConfig()
LEXICAL_CONFIG = LexicalScoringConfig()

class PageIndexExclusion(StrEnum):
    OFFTOPIC = "offtopic"
    NON_ENGLISH = "non_english"
    TOO_SHORT = "too_short"

@dataclass(frozen=True)
class PageVerdict:
    language: Language
    relevance: float
    token_count: int = HEURISTIC_CONFIG.min_tokens

    @property
    def should_index(self) -> bool:
        return self.index_exclusion is None

    @property
    def should_follow_links(self) -> bool:
        return self.is_relevant

    @property
    def index_exclusion(self) -> PageIndexExclusion | None:
        if not self.is_relevant:
            return PageIndexExclusion.OFFTOPIC
        if not self.has_enough_text:
            return PageIndexExclusion.TOO_SHORT
        if not self.is_english:
            return PageIndexExclusion.NON_ENGLISH
        return None

    @property
    def is_english(self) -> bool:
        return self.language is Language.EN

    @property
    def is_relevant(self) -> bool:
        return self.relevance >= REL_THRESHOLD

    @property
    def has_enough_text(self) -> bool:
        return self.token_count >= HEURISTIC_CONFIG.min_tokens

def _check_nltk_stopwords() -> None:
    try:
        stopwords.words("english")
        stopwords.words("german")
    except LookupError:
        nltk.download("stopwords")

def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in HEURISTIC_CONFIG.token_re.findall(text)]

def _language_from_attribute(lang_attribute: str) -> Language:
    lang = lang_attribute.lower()
    if lang.startswith("en"):
        return Language.EN
    if lang.startswith("de"):
        return Language.DE
    return Language.UNKNOWN

def load_stopwords() -> tuple[set[str], set[str]]:
    global _STOPWORDS

    if _STOPWORDS is None:
        _check_nltk_stopwords()
        german_stopwords = set(stopwords.words("german"))
        english_stopwords = set(stopwords.words("english"))

        common = sorted(german_stopwords & english_stopwords)
        english_stopwords.difference_update(common)
        german_stopwords.difference_update(common)
        _STOPWORDS = german_stopwords, english_stopwords

    return _STOPWORDS

def detect_language(
    tokens: list[str],
    lang_attribute: str | None = None,
) -> Language:
    if lang_attribute:
        return _language_from_attribute(lang_attribute)

    if len(tokens) < HEURISTIC_CONFIG.min_tokens:
        return Language.UNKNOWN

    german_stopwords, english_stopwords = load_stopwords()
    en = sum(t in english_stopwords for t in tokens)
    de = sum(t in german_stopwords for t in tokens)

    if en >= 5 and en >= de:
        return Language.EN
    if de >= 5 and de >= en:
        return Language.DE

    return Language.UNKNOWN

def lexical_relevance_score(
    url: str,
    title: str,
    text: str,
    *,
    description: str = "",
    h1: str = "",
) -> float:
    if not (
        has_tuebingen(url)
        or has_tuebingen(title)
        or has_tuebingen(description)
        or has_tuebingen(h1)
        or has_tuebingen(text)
    ):
        return 0.0

    features = {
        "url_has_tuebingen": has_tuebingen(url),
        "title_has_tuebingen": has_tuebingen(title),
        "description_has_tuebingen": has_tuebingen(description),
        "h1_has_tuebingen": has_tuebingen(h1),
    }
    score = sum(w for name, w in LEXICAL_CONFIG.feature_weights.items() if features[name])
    score += min(tuebingen_hits(text), 10)

    return score

def page_score(
    url: str,
    title: str,
    text: str,
    tokens: list[str],
    lang_attribute: str | None = None,
    *,
    description: str = "",
    h1: str = "",
) -> tuple[Language, float]:
    lang = detect_language(tokens, lang_attribute)
    lexical = lexical_relevance_score(
        url,
        title,
        text,
        description=description,
        h1=h1,
    )
    semantic_text = " ".join(part for part in (description, h1, text) if part)
    rel = 0.0

    if lexical > 0.0:
        # known-relevant page: the model only refines the lexical score
        sim = topic_similarity(title, semantic_text)
        floor = SEMANTIC_CONFIG.lexical_floor
        rel = lexical * (floor + (1.0 - floor) * sim)
    elif lang is Language.EN:
        # no lexical signal, the model admits clearly on-topic English pages
        sim = topic_similarity(title, semantic_text)
        threshold = SEMANTIC_CONFIG.admit_threshold
        if sim >= threshold:
            rel = (
                REL_THRESHOLD
                + SEMANTIC_CONFIG.admit_span
                * (sim - threshold)
                / (1.0 - threshold)
            )

    return lang, rel

def classify_page(
    url: str,
    title: str,
    text: str,
    lang_attribute: str | None = None,
    *,
    description: str = "",
    h1: str = "",
) -> PageVerdict:
    tokens = _tokenize(text)
    lang, relevance = page_score(
        url,
        title,
        text,
        tokens,
        lang_attribute,
        description=description,
        h1=h1,
    )
    return PageVerdict(language=lang, relevance=relevance, token_count=len(tokens))
