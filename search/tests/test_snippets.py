from tuebingen_search.snippets import best_snippet
from tuebingen_search.tokenizer import stem


def test_snippet_centers_on_best_matching_window():
    filler = "word " * 200
    text = filler + "the famous castle museum of the town " + filler
    snippet, highlights = best_snippet(text, {stem("castle"), stem("museum")})

    assert "castle" in snippet
    assert "museum" in snippet
    assert len(highlights) == 2


def test_snippet_highlight_offsets_match_terms():
    text = "The castle of Tübingen overlooks the river."
    snippet, highlights = best_snippet(text, {stem("castle"), stem("river")})

    highlighted = {snippet[start:end].lower() for start, end in highlights}
    assert highlighted == {"castle", "river"}


def test_snippet_matches_inflected_forms():
    text = "Many attractions are listed in the city guide."
    snippet, highlights = best_snippet(text, {stem("attraction")})
    assert {snippet[s:e].lower() for s, e in highlights} == {"attractions"}


def test_snippet_without_matches_returns_leading_text():
    snippet, highlights = best_snippet("Just some unrelated words here.", {stem("zzz")})
    assert snippet.startswith("Just some")
    assert highlights == []


def test_snippet_empty_text():
    snippet, highlights = best_snippet("", {stem("castle")})
    assert snippet == ""
    assert highlights == []
