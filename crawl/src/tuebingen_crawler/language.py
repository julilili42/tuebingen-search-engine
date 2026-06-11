"""Lightweight English-language detection.

Counts function words, which are frequent and language-specific, instead of
shipping a full language-id model. The ``lang`` attribute of the page is used
as an additional signal but never trusted on its own.
"""

from __future__ import annotations

ENGLISH_FUNCTION_WORDS = {
    "the", "of", "and", "to", "in", "is", "was", "that", "for", "on", "are",
    "with", "as", "his", "her", "they", "at", "be", "this", "have", "from",
    "or", "by", "not", "but", "what", "all", "were", "when", "your", "can",
    "there", "an", "which", "their", "has", "more", "will", "about", "you",
    "it", "he", "she", "we", "been", "than", "its", "also", "into", "only",
}

GERMAN_FUNCTION_WORDS = {
    "der", "die", "das", "und", "ist", "von", "den", "im", "mit", "auf",
    "für", "des", "ein", "eine", "dem", "nicht", "auch", "sich", "es", "ich",
    "wird", "sind", "einer", "einem", "einen", "als", "aus", "bei",
    "nach", "wie", "zum", "zur", "über", "wurde", "werden", "oder", "aber",
    "noch", "nur", "sie", "er", "wir", "kann", "wenn", "durch", "haben",
}

MIN_TOKENS = 30
MIN_ENGLISH_RATIO = 0.12


def is_english(text: str, lang_attribute: str = "") -> bool:
    """Return True if the page text is predominantly English."""
    lang = lang_attribute.split("-")[0].strip().lower()

    tokens = [token.lower() for token in text.split()]
    if len(tokens) < MIN_TOKENS:
        # Too little text for a reliable ratio; fall back to the declared lang.
        return lang == "en"

    english_hits = sum(1 for token in tokens if token in ENGLISH_FUNCTION_WORDS)
    german_hits = sum(1 for token in tokens if token in GERMAN_FUNCTION_WORDS)
    english_ratio = english_hits / len(tokens)

    if english_hits <= german_hits:
        return False
    if english_ratio >= MIN_ENGLISH_RATIO:
        return True
    # Borderline ratio: accept only if the page declares itself as English.
    return lang == "en" and english_ratio >= MIN_ENGLISH_RATIO / 2
