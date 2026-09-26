import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app import db as db_module
from app.main import app
from app.services.indexer import index_document

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_documents.json"


@pytest.fixture
async def db():
    database = db_module.in_memory_client()["test_search"]
    await db_module.ensure_indexes(database)
    db_module.set_db(database)
    yield database
    db_module.set_db(None)


@pytest.fixture
async def seeded_db(db):
    for doc in json.loads(SAMPLE.read_text()):
        await index_document(db, doc)
    return db


@pytest.fixture
async def client(db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
