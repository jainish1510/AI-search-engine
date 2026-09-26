"""MongoDB connection management (async, via Motor)."""
from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

from .config import settings

_client: AsyncIOMotorClient | None = None
_db: Any = None


def get_db() -> Any:
    """FastAPI dependency returning the active database handle."""
    if _db is None:
        raise RuntimeError("Database not initialised; call connect() first")
    return _db


def set_db(db: Any) -> None:
    """Use an existing database handle (used by tests with mongomock)."""
    global _db
    _db = db


def in_memory_client() -> Any:
    """In-memory MongoDB (``MONGODB_URI=mongomock://``) for demos and tests; data is not persisted."""
    from mongomock.collection import BulkOperationBuilder
    from mongomock_motor import AsyncMongoMockClient

    # pymongo >= 4.11 passes ``sort`` to bulk updates, which mongomock does not accept yet.
    if not getattr(BulkOperationBuilder.add_update, "_patched", False):
        original = BulkOperationBuilder.add_update

        def add_update(self, *args, sort=None, **kwargs):
            return original(self, *args, **kwargs)

        add_update._patched = True
        BulkOperationBuilder.add_update = add_update
    return AsyncMongoMockClient()


async def connect() -> Any:
    global _client, _db
    if _db is None:
        if settings.mongodb_uri.startswith("mongomock://"):
            _client = in_memory_client()
        else:
            _client = AsyncIOMotorClient(settings.mongodb_uri, tz_aware=True)
        _db = _client[settings.mongodb_db]
    await ensure_indexes(_db)
    return _db


async def close() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client, _db = None, None


async def ensure_indexes(db: Any) -> None:
    await db.postings.create_index([("term", ASCENDING), ("doc_id", ASCENDING)], unique=True)
    await db.postings.create_index([("doc_id", ASCENDING)])
    await db.vocab.create_index([("freq", DESCENDING)])
    await db.vocab.create_index([("first", ASCENDING), ("len", ASCENDING)])
    await db.documents.create_index([("tags", ASCENDING)])
    await db.documents.create_index([("created_at", DESCENDING)])
    await db.queries.create_index([("count", DESCENDING)])
