"""HTTP API and web user interface."""

from __future__ import annotations

import logging
import os
from collections import Counter
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse

from .search import SearchEngine

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    index_path = os.environ.get("INDEX_PATH", "index.bin")
    logger.info("Loading index from %s", index_path)
    app.state.engine = SearchEngine(index_path)
    yield


app = FastAPI(title="Tübingen Search", lifespan=lifespan)


@app.get("/api/search")
def search_api(
    q: str = Query(min_length=1),
    top_n: int = Query(100, ge=1, le=100),
    host: str | None = Query(None, description="restrict results to one host"),
):
    engine: SearchEngine = app.state.engine
    response = engine.retrieve(q, top_n=top_n)

    facets = Counter(result.host for result in response.results)
    results = response.results
    if host:
        results = [result for result in results if result.host == host]

    return {
        "query_terms": response.query_terms,
        "expansion_terms": response.expansion_terms,
        "completions": response.completions,
        "suggestions": engine.suggest_queries(q, response.expansion_terms),
        "total_matches": response.total_matches,
        "facets": facets.most_common(12),
        "results": [asdict(result) for result in results],
    }


@app.get("/health")
def health():
    return {"status": "ok", "documents": app.state.engine.doc_count}


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/spotlight")
def spotlight():
    return FileResponse(STATIC_DIR / "spotlight.html")
