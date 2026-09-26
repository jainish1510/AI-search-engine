"""Natural-language query processing.

Turns a raw user query such as

    how do I deploy "react app" to docker -kubernetes tag:devops

into a structured :class:`ParsedQuery` with required phrases, excluded terms,
tag filters, a detected intent and expanded (synonym) terms.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .text import analyze, normalize, raw_words, stem, tokenize

_PHRASE_RE = re.compile(r'"([^"]+)"')
_FILTER_RE = re.compile(r"(?<!\S)(tag|title):(\"[^\"]+\"|\S+)", re.IGNORECASE)
_EXCLUDE_RE = re.compile(r"(?<!\S)-(\w[\w.+#-]*)")

QUESTION_WORDS = {"what", "why", "how", "when", "where", "who", "which", "whom", "whose"}
_QUESTION_STARTERS = QUESTION_WORDS | {
    "is", "are", "can", "could", "does", "do", "should", "would", "will", "did", "explain", "define",
}
_NAVIGATIONAL_HINTS = {"login", "homepage", "website", "site", "official", "download", "docs", "documentation"}
_TRANSACTIONAL_HINTS = {"buy", "price", "pricing", "install", "download", "subscribe", "order", "cost"}
_COMPARISON_HINTS = {"vs", "versus", "compare", "comparison", "difference", "differences", "better"}
# Conversational filler that carries no search meaning ("can you please tell me about ...").
_FILLER = {"please", "tell", "show", "find", "give", "explain", "know", "want", "need", "like", "looking",
           "anyone", "someone", "thing", "things"}

# Small domain synonym table used for query expansion. Keys and values are
# surface words; expansion terms are added with a reduced weight.
SYNONYMS: dict[str, list[str]] = {
    "ai": ["artificial intelligence", "machine learning"],
    "ml": ["machine learning"],
    "js": ["javascript"],
    "javascript": ["js"],
    "db": ["database"],
    "database": ["db"],
    "car": ["automobile", "vehicle"],
    "automobile": ["car"],
    "fast": ["quick", "performance"],
    "quick": ["fast"],
    "bug": ["error", "defect"],
    "error": ["bug", "exception"],
    "doc": ["document", "documentation"],
    "docs": ["documentation"],
    "api": ["interface", "endpoint"],
    "k8s": ["kubernetes"],
    "kubernetes": ["k8s"],
    "nlp": ["natural language processing"],
    "search": ["retrieval"],
    "retrieval": ["search"],
    "movie": ["film"],
    "film": ["movie"],
    "big": ["large"],
    "large": ["big"],
    "small": ["tiny", "little"],
    "begin": ["start"],
    "start": ["begin"],
    "tutorial": ["guide", "introduction"],
    "guide": ["tutorial"],
}


@dataclass
class ParsedQuery:
    raw: str
    terms: list[str] = field(default_factory=list)  # stemmed search terms (deduplicated, ordered)
    surface_terms: list[str] = field(default_factory=list)  # the words those stems came from
    # Each phrase is a list of (stem, offset) pairs; offsets are relative word positions,
    # so stop words inside a phrase ("state of the art") still constrain adjacency.
    phrases: list[list[tuple[str, int]]] = field(default_factory=list)
    phrase_texts: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)  # stemmed terms that must not appear
    tags: list[str] = field(default_factory=list)
    title_terms: list[str] = field(default_factory=list)  # stems that must appear in the title
    expansions: dict[str, list[str]] = field(default_factory=dict)  # stem -> expanded stems
    intent: str = "informational"
    is_question: bool = False

    @property
    def is_empty(self) -> bool:
        return not (self.terms or self.phrases or self.title_terms or self.tags)

    def all_positive_terms(self) -> list[str]:
        seen: dict[str, None] = {}
        for term in [*self.terms, *self.title_terms, *(t for p in self.phrases for t, _ in p)]:
            seen.setdefault(term, None)
        return list(seen)

    def to_dict(self) -> dict:
        return {
            "raw": self.raw,
            "terms": self.terms,
            "keywords": self.surface_terms,
            "phrases": self.phrase_texts,
            "excluded": self.excluded,
            "tags": self.tags,
            "title_terms": self.title_terms,
            "expansions": self.expansions,
            "intent": self.intent,
            "is_question": self.is_question,
        }


def detect_intent(words: list[str]) -> tuple[str, bool]:
    """Classify the query as question / comparison / transactional / navigational / informational."""
    if not words:
        return "informational", False
    word_set = set(words)
    is_question = words[0] in _QUESTION_STARTERS or bool(word_set & QUESTION_WORDS)
    if word_set & _COMPARISON_HINTS:
        return "comparison", is_question
    if is_question:
        return "question", True
    if word_set & _TRANSACTIONAL_HINTS:
        return "transactional", False
    if word_set & _NAVIGATIONAL_HINTS:
        return "navigational", False
    return "informational", False


def parse_query(raw: str, expand: bool = True) -> ParsedQuery:
    query = ParsedQuery(raw=raw)
    text = raw

    for match in _FILTER_RE.finditer(text):
        kind, value = match.group(1).lower(), match.group(2).strip('"')
        if kind == "tag":
            query.tags.append(normalize(value).strip())
        else:
            query.title_terms.extend(t for t in analyze(value) if t not in query.title_terms)
    text = _FILTER_RE.sub(" ", text)

    for match in _PHRASE_RE.finditer(text):
        tokens = tokenize(match.group(1))
        if len(tokens) > 1:
            query.phrases.append([(t.term, t.position - tokens[0].position) for t in tokens])
            query.phrase_texts.append(match.group(1).strip())
        elif tokens:  # a quoted single word is just a normal term
            text += " " + match.group(1)
    text = _PHRASE_RE.sub(" ", text)

    for match in _EXCLUDE_RE.finditer(text):
        query.excluded.extend(t for t in analyze(match.group(1)) if t not in query.excluded)
    text = _EXCLUDE_RE.sub(" ", text)

    words = raw_words(raw)
    query.intent, query.is_question = detect_intent(words)

    phrase_terms = {t for phrase in query.phrases for t, _ in phrase}
    for token in tokenize(text):
        if token.surface in _FILLER or token.surface in QUESTION_WORDS:
            continue
        if token.term in query.excluded or token.term in phrase_terms or token.term in query.terms:
            continue
        query.terms.append(token.term)
        query.surface_terms.append(token.surface)

    # If filler removal ate everything (e.g. "show me things"), fall back to all tokens.
    if not query.terms and not query.phrases and not query.title_terms:
        for token in tokenize(text):
            if token.term not in query.terms and token.term not in query.excluded:
                query.terms.append(token.term)
                query.surface_terms.append(token.surface)

    if expand:
        for surface, term in zip(query.surface_terms, query.terms):
            expanded: list[str] = []
            for synonym in SYNONYMS.get(surface, []):
                for syn_term in analyze(synonym):
                    if syn_term not in query.terms and syn_term not in expanded and syn_term not in query.excluded:
                        expanded.append(syn_term)
            if expanded:
                query.expansions[term] = expanded
    return query


__all__ = ["ParsedQuery", "parse_query", "detect_intent", "SYNONYMS", "stem"]
