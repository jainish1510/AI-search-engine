"""Document CRUD and bulk indexing endpoints."""
from __future__ import annotations

from typing import Any

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from ..db import get_db
from ..schemas import BulkIn, DocumentIn, DocumentOut, DocumentUpdate, document_out
from ..services import indexer, jobs

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _object_id(doc_id: str) -> ObjectId:
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return ObjectId(doc_id)


@router.get("")
async def list_documents(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tag: str | None = None,
    db: Any = Depends(get_db),
) -> dict:
    query = {"tags": tag.lower()} if tag else {}
    total = await db.documents.count_documents(query)
    cursor = db.documents.find(query).sort("created_at", -1).skip((page - 1) * size).limit(size)
    items = [document_out(doc).model_dump() async for doc in cursor]
    return {"total": total, "page": page, "size": size, "items": items}


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(payload: DocumentIn, db: Any = Depends(get_db)) -> DocumentOut:
    doc = await indexer.index_document(db, payload.model_dump())
    return document_out(doc)


@router.post("/bulk", status_code=status.HTTP_202_ACCEPTED)
async def bulk_index(payload: BulkIn, background: BackgroundTasks, db: Any = Depends(get_db)) -> dict:
    """Queue documents for asynchronous indexing; poll ``/api/jobs/{id}`` for progress."""
    documents = [d.model_dump() for d in payload.documents]
    job_id = await jobs.create_job(db, len(documents))
    background.add_task(jobs.run_bulk_index, db, job_id, documents)
    return {"job_id": job_id, "status": "queued", "total": len(documents)}


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: str, db: Any = Depends(get_db)) -> DocumentOut:
    doc = await db.documents.find_one({"_id": _object_id(doc_id)})
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document_out(doc)


@router.patch("/{doc_id}", response_model=DocumentOut)
async def update_document(doc_id: str, payload: DocumentUpdate, db: Any = Depends(get_db)) -> DocumentOut:
    doc = await indexer.update_document(db, _object_id(doc_id), payload.model_dump(exclude_unset=True))
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document_out(doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: str, db: Any = Depends(get_db)) -> None:
    if await indexer.remove_document(db, _object_id(doc_id)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
