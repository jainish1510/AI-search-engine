"""Query execution and relevance ranking.

Ranking uses BM25F (BM25 with per-field weights and length normalisation for
the title and body) combined with:

* a query-coverage factor rewarding documents that match more query terms,
* a proximity bonus when matched terms occur close together,
* a phrase bonus for quoted phrases (which are also required matches),
* down-weighted synonym expansion terms.
"""
from __future__ import annotations

import math
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..config import settings
from ..nlp import ParsedQuery, parse_query, tokenize
from ..nlp.spelling import best_correction
from ..nlp.text import is_stop_word
from .indexer import document_frequencies, get_stats

EXPANSION_WEIGHT = 0.35
PHRASE_BONUS = 1.5
PROXIMITY_WEIGHT = 0.6
SNIPPET_WORDS = 32


@dataclass
class Candidate:
    doc_id: Any
    fields: dict[str, dict[str, list[int]]] = field(default_factory=dict)  # term -> field -> positions
    score: float = 0.0
    matched: set[str] = field(default_factory=set)


def idf(df: int, n_docs: int) -> float:
    return math.log(1 + (n_docs - df + 0.5) / (df + 0.5))


def _phrase_in(positions: dict[str, list[int]], phrase: list[tuple[str, int]]) -> bool:
    first_term, _ = phrase[0]
    for start in positions.get(first_term, []):
        if all(start + offset in set(positions.get(term, [])) for term, offset in phrase[1:]):
            return True
    return False


def phrase_matches(candidate: Candidate, phrase: list[tuple[str, int]]) -> bool:
    for field_name in ("title", "body"):
        field_positions = {t: f.get(field_name, []) for t, f in candidate.fields.items()}
        if _phrase_in(field_positions, phrase):
            return True
    return False


def min_span(position_lists: list[list[int]]) -> int | None:
    """Smallest window (in words) containing at least one position from every list."""
    lists = [sorted(p) for p in position_lists if p]
    if len(lists) < 2 or len(lists) != len(position_lists):
        return None
    events = sorted((pos, i) for i, positions in enumerate(lists) for pos in positions)
    counts: Counter[int] = Counter()
    best, left, covered = None, 0, 0
    for pos, idx in events:
        counts[idx] += 1
        if counts[idx] == 1:
            covered += 1
        while covered == len(lists):
            span = pos - events[left][0] + 1
            best = span if best is None else min(best, span)
            lidx = events[left][1]
            counts[lidx] -= 1
            if counts[lidx] == 0:
                covered -= 1
            left += 1
    return best


def bm25f(
    candidate: Candidate,
    term_weights: dict[str, float],
    dfs: dict[str, int],
    doc_len: dict[str, int],
    stats: dict,
) -> float:
    n_docs = max(stats.get("doc_count", 0), 1)
    avg_title = max(stats.get("title_len", 0) / n_docs, 1.0)
    avg_body = max(stats.get("body_len", 0) / n_docs, 1.0)
    k1 = settings.bm25_k1
    score = 0.0
    for term, weight in term_weights.items():
        fields = candidate.fields.get(term)
        if not fields:
            continue
        tf_title, tf_body = len(fields.get("title", [])), len(fields.get("body", []))
        norm_title = 1 - settings.title_b + settings.title_b * doc_len.get("title", 0) / avg_title
        norm_body = 1 - settings.body_b + settings.body_b * doc_len.get("body", 0) / avg_body
        weighted_tf = settings.title_weight * tf_title / norm_title + settings.body_weight * tf_body / norm_body
        score += weight * idf(dfs.get(term, 0), n_docs) * weighted_tf / (k1 + weighted_tf)
    return score


def build_snippet(text: str, highlight_terms: set[str], max_words: int = SNIPPET_WORDS) -> list[dict]:
    """Return the most relevant passage of ``text`` as highlight segments.

    The result is a list of ``{"text": str, "highlight": bool}`` so the client
    can render highlights without injecting HTML.
    """
    if not text:
        return []
    words = list(re.finditer(r"\S+", text))
    tokens = tokenize(text)
    hits = [t for t in tokens if t.term in highlight_terms]

    start_word = 0
    if hits and len(words) > max_words:
        # Map char offsets to word indexes, then find the window with the most distinct matches.
        word_starts = [w.start() for w in words]

        def word_index(char_offset: int) -> int:
            lo, hi = 0, len(word_starts) - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if word_starts[mid] <= char_offset:
                    lo = mid
                else:
                    hi = mid - 1
            return lo

        hit_words = [(word_index(t.start), t.term) for t in hits]
        best_score, best_start = -1.0, 0
        for i, (w_idx, _) in enumerate(hit_words):
            window = [term for idx, term in hit_words[i:] if idx < w_idx + max_words]
            score = len(set(window)) + 0.1 * len(window)
            if score > best_score:
                best_score, best_start = score, w_idx
        start_word = max(0, min(best_start - 4, len(words) - max_words))

    end_word = min(len(words), start_word + max_words)
    char_start = words[start_word].start()
    char_end = words[end_word - 1].end()
    segments: list[dict] = []
    if start_word > 0:
        segments.append({"text": "… ", "highlight": False})
    cursor = char_start
    for token in hits:
        if token.start < char_start or token.end > char_end:
            continue
        # Map normalized-token offsets back (normalization preserves length for most text).
        if cursor < token.start:
            segments.append({"text": text[cursor : token.start], "highlight": False})
        segments.append({"text": text[token.start : token.end], "highlight": True})
        cursor = token.end
    if cursor < char_end:
        segments.append({"text": text[cursor:char_end], "highlight": False})
    if end_word < len(words):
        segments.append({"text": " …", "highlight": False})
    return segments


async def suggest_correction(db: Any, parsed: ParsedQuery, dfs: dict[str, int]) -> str | None:
    """Build a "did you mean" query when some query words are not in the index."""
    corrected_any = False
    replacements: dict[str, str] = {}
    for surface, term in zip(parsed.surface_terms, parsed.terms):
        if dfs.get(term, 0) > 0 or len(surface) < 4 or not surface.isalpha():
            continue
        cursor = db.vocab.find(
            {"first": {"$in": list({surface[0], surface[1]})}, "len": {"$gte": len(surface) - 2, "$lte": len(surface) + 2}},
            {"freq": 1},
        ).sort("freq", -1).limit(5000)
        candidates = {row["_id"]: row["freq"] async for row in cursor}
        fix = best_correction(surface, candidates)
        if fix:
            replacements[surface] = fix
            corrected_any = True
    if not corrected_any:
        return None

    def replace(match: re.Match) -> str:
        word = match.group(0)
        fixed = replacements.get(word.lower())
        return fixed if fixed else word

    return re.sub(r"[A-Za-z]+", replace, parsed.raw)


async def log_query(db: Any, raw: str, total: int) -> None:
    normalized = " ".join(raw.lower().split())
    if not normalized or total == 0:
        return
    await db.queries.update_one(
        {"_id": normalized},
        {"$inc": {"count": 1}, "$set": {"last_results": total, "last_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


async def search(
    db: Any,
    raw_query: str,
    page: int = 1,
    size: int = 10,
    tags: list[str] | None = None,
    expand: bool = True,
    log: bool = True,
) -> dict:
    started = time.perf_counter()
    parsed = parse_query(raw_query, expand=expand)
    for tag in tags or []:
        tag = tag.strip().lower()
        if tag and tag not in parsed.tags:
            parsed.tags.append(tag)

    stats = await get_stats(db)
    positive = parsed.all_positive_terms()
    expansion_terms = sorted({t for terms in parsed.expansions.values() for t in terms} - set(positive))
    lookup = positive + expansion_terms + parsed.excluded

    # Gather postings for every term the query references.
    candidates: dict[Any, Candidate] = {}
    excluded_docs: set[Any] = set()
    if lookup:
        async for row in db.postings.find({"term": {"$in": lookup}}):
            doc_id = row["doc_id"]
            if row["term"] in parsed.excluded:
                excluded_docs.add(doc_id)
                continue
            cand = candidates.setdefault(doc_id, Candidate(doc_id))
            cand.fields[row["term"]] = {"title": row.get("title", []), "body": row.get("body", [])}
    elif parsed.tags:
        # Pure tag browsing ("tag:python"): every tagged document is a candidate.
        async for row in db.documents.find({"tags": {"$all": parsed.tags}}, {"_id": 1}):
            candidates[row["_id"]] = Candidate(row["_id"])

    for doc_id in excluded_docs:
        candidates.pop(doc_id, None)

    # Hard constraints: phrases and title: filters must match.
    def satisfies(cand: Candidate) -> bool:
        if not cand.fields and lookup:
            return False
        if any(not cand.fields.get(t, {}).get("title") for t in parsed.title_terms):
            return False
        return all(phrase_matches(cand, phrase) for phrase in parsed.phrases)

    candidates = {d: c for d, c in candidates.items() if satisfies(c)}

    # Load lengths + tags for remaining candidates (and apply tag filters).
    meta: dict[Any, dict] = {}
    if candidates:
        tag_filter: dict = {"_id": {"$in": list(candidates)}}
        if parsed.tags:
            tag_filter["tags"] = {"$all": parsed.tags}
        async for row in db.documents.find(tag_filter, {"length": 1, "tags": 1, "created_at": 1}):
            meta[row["_id"]] = row
        candidates = {d: c for d, c in candidates.items() if d in meta}

    dfs = await document_frequencies(db, positive + expansion_terms)
    term_weights: dict[str, float] = {t: 1.0 for t in positive}
    for t in expansion_terms:
        term_weights[t] = EXPANSION_WEIGHT
    core_terms = parsed.terms or positive
    n_docs = max(stats.get("doc_count", 0), 1)

    for cand in candidates.values():
        doc_meta = meta[cand.doc_id]
        score = bm25f(cand, term_weights, dfs, doc_meta.get("length", {}), stats)
        cand.matched = {t for t in positive if t in cand.fields}
        if core_terms:
            # Treat a term as matched when it or one of its synonyms is present.
            hit = sum(
                1
                for t in core_terms
                if t in cand.fields or any(s in cand.fields for s in parsed.expansions.get(t, []))
            )
            coverage = hit / len(core_terms)
            score *= 0.4 + 0.6 * coverage**2
        matched_core = [t for t in core_terms if t in cand.fields]
        if len(matched_core) > 1:
            span = min_span([cand.fields[t].get("body", []) for t in matched_core])
            if span is not None:
                score += PROXIMITY_WEIGHT * len(matched_core) / span
        for phrase in parsed.phrases:
            score += PHRASE_BONUS * sum(idf(dfs.get(t, 0), n_docs) for t, _ in phrase) / len(phrase)
        if not lookup:
            score = 1.0  # tag-only browse
        cand.score = score

    ranked = sorted(candidates.values(), key=lambda c: (-c.score, str(c.doc_id)))
    total = len(ranked)

    facets = Counter(tag for c in ranked for tag in meta[c.doc_id].get("tags", []))

    page = max(page, 1)
    page_items = ranked[(page - 1) * size : page * size]
    docs: dict[Any, dict] = {}
    if page_items:
        async for row in db.documents.find({"_id": {"$in": [c.doc_id for c in page_items]}}):
            docs[row["_id"]] = row

    highlight_terms = set(positive) | set(expansion_terms)
    max_score = ranked[0].score if ranked else 1.0
    results = []
    for cand in page_items:
        doc = docs.get(cand.doc_id)
        if doc is None:
            continue
        results.append(
            {
                "id": str(doc["_id"]),
                "title": doc["title"],
                "title_segments": build_snippet(doc["title"], highlight_terms, max_words=10_000),
                "url": doc.get("url"),
                "tags": doc.get("tags", []),
                "keywords": [k["text"] for k in doc.get("keywords", [])[:5]],
                "snippet": build_snippet(doc["body"], highlight_terms),
                "score": round(cand.score, 4),
                "relevance": round(cand.score / max_score, 4) if max_score > 0 else 0.0,
                "matched_terms": sorted(cand.matched),
                "created_at": doc.get("created_at"),
            }
        )

    did_you_mean = None
    if parsed.terms and (total == 0 or any(dfs.get(t, 0) == 0 for t in parsed.terms)):
        did_you_mean = await suggest_correction(db, parsed, dfs)

    if log and page == 1:
        await log_query(db, raw_query, total)

    return {
        "query": raw_query,
        "total": total,
        "page": page,
        "size": size,
        "pages": math.ceil(total / size) if size else 0,
        "took_ms": round((time.perf_counter() - started) * 1000, 2),
        "results": results,
        "facets": [{"tag": t, "count": c} for t, c in facets.most_common(20)],
        "did_you_mean": did_you_mean,
        "analysis": parsed.to_dict(),
    }


async def autocomplete(db: Any, prefix: str, limit: int = 8) -> list[str]:
    """Suggest full queries for a partially typed query."""
    text = prefix.lower().lstrip()
    if not text.strip():
        return []
    suggestions: dict[str, None] = {}

    # 1. Popular past queries starting with the same text.
    pattern = "^" + re.escape(" ".join(text.split()))
    async for row in db.queries.find({"_id": {"$regex": pattern}}).sort("count", -1).limit(limit):
        suggestions.setdefault(row["_id"], None)

    # 2. Complete the last word from the index vocabulary.
    head, _, last = text.rpartition(" ")
    if last and len(suggestions) < limit:
        cursor = db.vocab.find({"_id": {"$regex": "^" + re.escape(last)}}).sort("freq", -1).limit(limit * 3)
        async for row in cursor:
            word = row["_id"]
            if is_stop_word(word) or word == last and not head:
                continue
            suggestions.setdefault(f"{head} {word}".strip(), None)
            if len(suggestions) >= limit:
                break
    return list(suggestions)[:limit]
