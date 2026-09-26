"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import json
import logging

from . import db
from .config import settings
from .routers import documents, search
from .seed import DEFAULT_DATA
from .services.indexer import index_document

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    database = await db.connect()
    if settings.seed_sample_data and await database.documents.estimated_document_count() == 0:
        for data in json.loads(DEFAULT_DATA.read_text(encoding="utf-8")):
            await index_document(database, data)
        log.info("Seeded sample documents from %s", DEFAULT_DATA)
    yield
    await db.close()


app = FastAPI(
    title="AI-Powered Search Engine",
    version="1.0.0",
    description="Full-text search with NLP query processing, keyword extraction and BM25F relevance ranking.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(search.router)
app.include_router(documents.router)


@app.get("/api/health", tags=["system"])
async def health() -> dict:
    await db.get_db().command("ping")
    return {"status": "ok"}
