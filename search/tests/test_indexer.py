import json
from pathlib import Path

import msgpack
import numpy as np
import pytest

from tuebingen_search.indexer import TITLE_WEIGHT, index, load_corpus
from tuebingen_search.tokenizer import stem

from conftest import CORPUS, write_corpus


def load_payload(index_path: str) -> dict:
    with Path(index_path).open("rb") as index_file:
        return msgpack.unpack(index_file, raw=False)


def test_index_stores_all_documents_with_urls(index_path):
    payload = load_payload(index_path)
    urls = [entry[0] for entry in payload["documents"]]
    assert urls == [url for url, _, _ in CORPUS]


def test_postings_are_doc_id_tf_pairs(index_path):
    payload = load_payload(index_path)
    castle = payload["postings"][stem("castle")]

    assert len(castle) % 2 == 0
    doc_ids = castle[::2]
    assert doc_ids == sorted(doc_ids)
    # castle appears in documents 0, 1 and 7
    assert doc_ids == [0, 1, 7]


def test_title_terms_are_weighted(index_path):
    payload = load_payload(index_path)
    punting = dict(zip(
        payload["postings"][stem("punting")][::2],
        payload["postings"][stem("punting")][1::2],
    ))
    # Document 6 ("Punting boats") has the term once in the title and once in
    # the body text: tf = TITLE_WEIGHT + 1.
    assert punting[6] == TITLE_WEIGHT + 1


def test_lsa_artifacts_are_written(index_path):
    payload = load_payload(index_path)
    vectors = np.load(index_path + ".npz")

    assert len(payload["lsa_vocab"]) >= 3
    assert vectors["doc_vectors"].shape == (
        len(CORPUS),
        vectors["term_vectors"].shape[1],
    )
    norms = np.linalg.norm(vectors["doc_vectors"], axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


def test_avg_doc_length_positive(index_path):
    payload = load_payload(index_path)
    assert payload["avg_doc_length"] > 0


def test_load_corpus_skips_missing_files(tmp_path, caplog):
    write_corpus(tmp_path)
    catalog = tmp_path / "pages.jsonl"
    records = catalog.read_text().splitlines()
    records.append(json.dumps(
        {"url": "https://gone.test/x", "path": "missing.html", "title": "", "description": ""}
    ))
    catalog.write_text("\n".join(records))

    documents = load_corpus(str(tmp_path))
    assert len(documents) == len(CORPUS)


def test_load_corpus_falls_back_to_html_scan(tmp_path):
    (tmp_path / "a.html").write_text(
        "<html><head><title>T</title></head><body><p>some text</p></body></html>"
    )
    documents = load_corpus(str(tmp_path))
    assert len(documents) == 1
    assert documents[0].title == "T"


def test_index_raises_on_empty_directory(tmp_path):
    with pytest.raises(ValueError):
        index(str(tmp_path), str(tmp_path / "index.bin"))
