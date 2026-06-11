import pytest
from fastapi.testclient import TestClient

from tuebingen_search.api import app


@pytest.fixture
def client(index_path, monkeypatch):
    monkeypatch.setenv("INDEX_PATH", index_path)
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_document_count(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["documents"] == 8


def test_search_returns_results_with_facets_and_suggestions(client):
    response = client.get("/api/search", params={"q": "castle"})
    assert response.status_code == 200

    data = response.json()
    assert data["results"]
    assert data["query_terms"]
    assert any(host == "site-a.test" for host, _ in data["facets"])

    top = data["results"][0]
    assert {"url", "title", "snippet", "highlights", "score", "matched_terms"} <= set(top)


def test_search_host_filter(client):
    response = client.get("/api/search", params={"q": "castle", "host": "site-c.test"})
    hosts = {result["host"] for result in response.json()["results"]}
    assert hosts == {"site-c.test"}


def test_search_requires_query(client):
    assert client.get("/api/search").status_code == 422


def test_home_serves_ui(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Tübingen" in response.text


def test_spotlight_serves_desktop_ui(client):
    response = client.get("/spotlight")
    assert response.status_code == 200
    assert "spotlight" in response.text.lower()


def test_search_results_include_score_breakdown(client):
    response = client.get("/api/search", params={"q": "weekly market"})
    top = response.json()["results"][0]
    assert {"bm25_score", "semantic_score", "proximity_score"} <= set(top)
