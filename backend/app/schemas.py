"""Request / response models."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class DocumentIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field("", max_length=1_000_000)
    url: str | None = Field(None, max_length=2048)
    tags: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title must not be blank")
        return value


class DocumentUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    body: str | None = Field(None, max_length=1_000_000)
    url: str | None = Field(None, max_length=2048)
    tags: list[str] | None = Field(None, max_length=50)


class Keyword(BaseModel):
    text: str
    score: float


class DocumentOut(BaseModel):
    id: str
    title: str
    body: str
    url: str | None = None
    tags: list[str] = []
    keywords: list[Keyword] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BulkIn(BaseModel):
    documents: list[DocumentIn] = Field(..., min_length=1, max_length=10_000)


class AnalyzeIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=1_000_000)
    top_k: int = Field(10, ge=1, le=50)


def document_out(doc: dict) -> DocumentOut:
    return DocumentOut(
        id=str(doc["_id"]),
        title=doc["title"],
        body=doc.get("body", ""),
        url=doc.get("url"),
        tags=doc.get("tags", []),
        keywords=doc.get("keywords", []),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )
