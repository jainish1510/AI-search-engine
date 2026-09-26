"""Document indexing: builds and maintains the inverted index in MongoDB.

Collections
-----------
documents  the stored documents plus extracted keywords and field lengths
postings   one row per (term, document): term positions in the title and body
terms      document frequency (df) per stemmed term
vocab      surface words with corpus frequency (autocomplete + spelling correction)
stats      corpus-wide counters used for BM25 length normalisation
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import UpdateOne

from ..nlp import extract_keywords, normalize, tokenize

STATS_ID = "corpus"


def _normalize_tags(tags: list[str] | None) -> list[str]:
    seen: dict[str, None] = {}
    for tag in tags or []:
        clean = normalize(tag).strip()
        if clean:
            seen.setdefault(clean, None)
    return list(seen)


async def get_stats(db: Any) -> dict:
    stats = await db.stats.find_one({"_id": STATS_ID})
    return stats or {"_id": STATS_ID, "doc_count": 0, "title_len": 0, "body_len": 0}


async def document_frequencies(db: Any, terms: list[str]) -> dict[str, int]:
    if not terms:
        return {}
    cursor = db.terms.find({"_id": {"$in": list(set(terms))}})
    return {row["_id"]: row["df"] async for row in cursor}


def _build_postings(title: str, body: str) -> tuple[dict[str, dict[str, list[int]]], Counter[str], int, int]:
    """Return {term: {"title": [...], "body": [...]}}, surface word counts and field lengths."""
    postings: dict[str, dict[str, list[int]]] = defaultdict(lambda: {"title": [], "body": []})
    surfaces: Counter[str] = Counter()
    title_tokens, body_tokens = tokenize(title), tokenize(body)
    for field_name, tokens in (("title", title_tokens), ("body", body_tokens)):
        for token in tokens:
            postings[token.term][field_name].append(token.position)
            surfaces[token.surface] += 1
    return postings, surfaces, len(title_tokens), len(body_tokens)


async def index_document(db: Any, data: dict, doc_id: ObjectId | None = None) -> dict:
    """Analyse and index a document; returns the stored document."""
    title, body = data["title"].strip(), data.get("body", "").strip()
    postings, surfaces, title_len, body_len = _build_postings(title, body)

    stats = await get_stats(db)
    dfs = await document_frequencies(db, list(postings))
    keywords = extract_keywords(
        f"{title}.\n{body}",
        top_k=10,
        doc_freq=lambda t: dfs.get(t, 0),
        total_docs=stats["doc_count"],
    )

    now = datetime.now(timezone.utc)
    document = {
        "_id": doc_id or ObjectId(),
        "title": title,
        "body": body,
        "url": data.get("url"),
        "tags": _normalize_tags(data.get("tags")),
        "keywords": [k.to_dict() for k in keywords],
        "length": {"title": title_len, "body": body_len},
        "created_at": data.get("created_at") or now,
        "updated_at": now,
    }
    await db.documents.insert_one(document)

    if postings:
        await db.postings.insert_many(
            [{"term": term, "doc_id": document["_id"], **fields} for term, fields in postings.items()]
        )
        await db.terms.bulk_write([UpdateOne({"_id": t}, {"$inc": {"df": 1}}, upsert=True) for t in postings])
    if surfaces:
        await db.vocab.bulk_write(
            [
                UpdateOne(
                    {"_id": word},
                    {"$inc": {"freq": count}, "$set": {"first": word[0], "len": len(word)}},
                    upsert=True,
                )
                for word, count in surfaces.items()
            ]
        )
    await db.stats.update_one(
        {"_id": STATS_ID},
        {"$inc": {"doc_count": 1, "title_len": title_len, "body_len": body_len}},
        upsert=True,
    )
    return document


async def remove_document(db: Any, doc_id: ObjectId) -> dict | None:
    """Remove a document and undo its contribution to the index. Returns the removed doc."""
    document = await db.documents.find_one_and_delete({"_id": doc_id})
    if document is None:
        return None
    terms = [row["term"] async for row in db.postings.find({"doc_id": doc_id}, {"term": 1})]
    await db.postings.delete_many({"doc_id": doc_id})
    if terms:
        await db.terms.bulk_write([UpdateOne({"_id": t}, {"$inc": {"df": -1}}) for t in terms])
        await db.terms.delete_many({"df": {"$lte": 0}})

    _, surfaces, _, _ = _build_postings(document["title"], document["body"])
    if surfaces:
        await db.vocab.bulk_write([UpdateOne({"_id": w}, {"$inc": {"freq": -c}}) for w, c in surfaces.items()])
        await db.vocab.delete_many({"freq": {"$lte": 0}})

    length = document.get("length", {})
    await db.stats.update_one(
        {"_id": STATS_ID},
        {"$inc": {"doc_count": -1, "title_len": -length.get("title", 0), "body_len": -length.get("body", 0)}},
    )
    return document


async def update_document(db: Any, doc_id: ObjectId, data: dict) -> dict | None:
    existing = await remove_document(db, doc_id)
    if existing is None:
        return None
    merged = {
        "title": data.get("title") or existing["title"],
        "body": data["body"] if data.get("body") is not None else existing["body"],
        "url": data["url"] if "url" in data else existing.get("url"),
        "tags": data["tags"] if data.get("tags") is not None else existing.get("tags", []),
        "created_at": existing.get("created_at"),
    }
    return await index_document(db, merged, doc_id=doc_id)
