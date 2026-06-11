from tuebingen_search.tokenizer import analyze, stem, tokenize, tokenize_with_offsets


def test_tokenize_lowercases_and_splits():
    assert tokenize("Tübingen's Old Town, est. 1477!") == [
        "tübingen", "old", "town", "est", "1477",
    ]


def test_tokenize_drops_single_characters():
    assert tokenize("a I x42") == ["x42"]


def test_tokenize_with_offsets_matches_source():
    text = "Visit the Castle"
    tokens = tokenize_with_offsets(text)
    assert [token for token, _, _ in tokens] == ["visit", "the", "castle"]
    for token, start, end in tokens:
        assert text[start:end].lower() == token


def test_stemming_conflates_word_forms():
    assert stem("attractions") == stem("attraction")
    assert stem("universities") == stem("university")


def test_analyze_removes_stopwords_and_stems():
    terms = analyze("The attractions of the university")
    assert "the" not in terms
    assert "of" not in terms
    assert terms == [stem("attractions"), stem("university")]
