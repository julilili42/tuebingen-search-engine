"""Query-dependent snippet selection with highlight offsets."""

from __future__ import annotations

from .tokenizer import stem, tokenize_with_offsets

SNIPPET_WINDOW_TOKENS = 45
FALLBACK_CHARS = 240


def best_snippet(
    text: str, query_stems: set[str]
) -> tuple[str, list[tuple[int, int]]]:
    """Pick the text window with the best query-term coverage.

    Returns the snippet and (start, end) highlight offsets relative to it.
    Windows are scored by unique matched stems first (coverage), total
    matches second (density).
    """
    tokens = tokenize_with_offsets(text)
    if not tokens:
        return text[:FALLBACK_CHARS].strip(), []

    stems = [stem(token) for token, _, _ in tokens]
    hit_indices = [i for i, token_stem in enumerate(stems) if token_stem in query_stems]

    if not hit_indices:
        end = tokens[min(SNIPPET_WINDOW_TOKENS, len(tokens)) - 1][2]
        return _cut(text, 0, end, len(tokens) > SNIPPET_WINDOW_TOKENS)[0], []

    best_start = hit_indices[0]
    best_score = (0, 0)
    for window_start in hit_indices:
        window_end = window_start + SNIPPET_WINDOW_TOKENS
        in_window = [i for i in hit_indices if window_start <= i < window_end]
        score = (len({stems[i] for i in in_window}), len(in_window))
        if score > best_score:
            best_score = score
            best_start = window_start

    # Add a little leading context so matches do not sit at the very edge.
    first_token = max(best_start - 5, 0)
    last_token = min(best_start + SNIPPET_WINDOW_TOKENS, len(tokens)) - 1

    snippet, offset_shift = _cut(
        text,
        tokens[first_token][1],
        tokens[last_token][2],
        truncated_end=last_token < len(tokens) - 1,
        truncated_start=first_token > 0,
    )

    highlights = [
        (tokens[i][1] - offset_shift, tokens[i][2] - offset_shift)
        for i in hit_indices
        if first_token <= i <= last_token
    ]
    return snippet, highlights


def _cut(
    text: str,
    start: int,
    end: int,
    truncated_end: bool,
    truncated_start: bool = False,
) -> tuple[str, int]:
    """Slice text and decorate with ellipses; returns (snippet, offset_shift)
    where offset_shift maps original offsets into snippet coordinates."""
    prefix = "… " if truncated_start else ""
    suffix = " …" if truncated_end else ""
    return prefix + text[start:end] + suffix, start - len(prefix)
