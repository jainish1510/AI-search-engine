"""Asynchronous bulk-indexing jobs, tracked in the ``jobs`` collection."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from .indexer import index_document

log = logging.getLogger(__name__)


async def create_job(db: Any, total: int) -> str:
    job_id = ObjectId()
    await db.jobs.insert_one(
        {
            "_id": job_id,
            "status": "queued",
            "total": total,
            "processed": 0,
            "failed": 0,
            "document_ids": [],
            "errors": [],
            "created_at": datetime.now(timezone.utc),
        }
    )
    return str(job_id)


async def run_bulk_index(db: Any, job_id: str, documents: list[dict]) -> None:
    oid = ObjectId(job_id)
    await db.jobs.update_one({"_id": oid}, {"$set": {"status": "running"}})
    for i, data in enumerate(documents):
        try:
            doc = await index_document(db, data)
            await db.jobs.update_one(
                {"_id": oid}, {"$inc": {"processed": 1}, "$push": {"document_ids": str(doc["_id"])}}
            )
        except Exception as exc:  # keep going; report per-document failures
            log.exception("Failed to index document %s of job %s", i, job_id)
            await db.jobs.update_one(
                {"_id": oid},
                {"$inc": {"processed": 1, "failed": 1}, "$push": {"errors": {"index": i, "error": str(exc)}}},
            )
    await db.jobs.update_one(
        {"_id": oid}, {"$set": {"status": "completed", "finished_at": datetime.now(timezone.utc)}}
    )


async def get_job(db: Any, job_id: str) -> dict | None:
    if not ObjectId.is_valid(job_id):
        return None
    job = await db.jobs.find_one({"_id": ObjectId(job_id)})
    if job:
        job["id"] = str(job.pop("_id"))
    return job
