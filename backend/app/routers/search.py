"""Search, autocomplete and NLP analysis endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..db import get_db
from ..nlp import extract_keywords, parse_query, tokenize
from ..schemas import AnalyzeIn
from ..services import jobs
from ..services.indexer import document_frequencies, get_stats
from ..services.search import autocomplete, search

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
async def search_documents(
    q: str = Query("", max_length=500),
    page: int = Query(1, ge=1, le=1000),
    size: int = Query(10, ge=1, le=50),
    tags: list[str] = Query(default_factory=list),
    expand: bool = True,
    db: Any = Depends(get_db),
) -> dict:
    return await search(db, q, page=page, size=size, tags=tags, expand=expand)


@router.get("/suggest")
async def suggest(q: str = Query("", max_length=200), limit: int = Query(8, ge=1, le=20), db: Any = Depends(get_db)) -> dict:
    return {"query": q, "suggestions": await autocomplete(db, q, limit)}


@router.get("/query/analyze")
async def analyze_query(q: str = Query(..., min_length=1, max_length=500)) -> dict:
    """Show how the NLP pipeline interprets a query (without executing it)."""
    return parse_query(q).to_dict()


@router.post("/analyze")
async def analyze_text(payload: AnalyzeIn, db: Any = Depends(get_db)) -> dict:
    """Extract keywords from arbitrary text, using corpus statistics for IDF."""
    tokens = tokenize(payload.text)
    stats = await get_stats(db)
    dfs = await document_frequencies(db, [t.term for t in tokens])
    keywords = extract_keywords(
        payload.text, top_k=payload.top_k, doc_freq=lambda t: dfs.get(t, 0), total_docs=stats["doc_count"]
    )
    return {
        "keywords": [k.to_dict() for k in keywords],
        "tokens": [{"surface": t.surface, "term": t.term, "position": t.position} for t in tokens[:500]],
        "token_count": len(tokens),
    }


@router.get("/jobs/{job_id}")
async def job_status(job_id: str, db: Any = Depends(get_db)) -> dict:
    job = await jobs.get_job(db, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/stats")
async def corpus_stats(db: Any = Depends(get_db)) -> dict:
    stats = await get_stats(db)
    n = stats.get("doc_count", 0)
    top_terms = [
        {"word": row["_id"], "freq": row["freq"]} async for row in db.vocab.find().sort("freq", -1).limit(15)
    ]
    popular = [
        {"query": row["_id"], "count": row["count"]} async for row in db.queries.find().sort("count", -1).limit(10)
    ]
    return {
        "documents": n,
        "unique_terms": await db.terms.count_documents({}),
        "avg_title_length": round(stats.get("title_len", 0) / n, 2) if n else 0,
        "avg_body_length": round(stats.get("body_len", 0) / n, 2) if n else 0,
        "top_words": top_terms,
        "popular_queries": popular,
    }
