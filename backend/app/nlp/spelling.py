"""Spelling correction helpers ("did you mean ...?")."""
from __future__ import annotations


def damerau_levenshtein(a: str, b: str, max_distance: int | None = None) -> int:
    """Optimal string alignment distance (insert/delete/substitute/transpose)."""
    if a == b:
        return 0
    if max_distance is not None and abs(len(a) - len(b)) > max_distance:
        return max_distance + 1
    prev_prev: list[int] = []
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev_prev[j - 2] + 1)
        if max_distance is not None and min(cur) > max_distance:
            return max_distance + 1
        prev_prev, prev = prev, cur
    return prev[-1]


def max_edits_for(word: str) -> int:
    return 0 if len(word) <= 3 else 1 if len(word) <= 6 else 2


def best_correction(word: str, candidates: dict[str, int]) -> str | None:
    """Pick the closest candidate (ties broken by frequency) within the allowed edit distance."""
    limit = max_edits_for(word)
    if limit == 0:
        return None
    best: tuple[int, int, str] | None = None
    for candidate, freq in candidates.items():
        if candidate == word:
            continue
        distance = damerau_levenshtein(word, candidate, limit)
        if distance <= limit:
            key = (distance, -freq, candidate)
            if best is None or key < best:
                best = key
    return best[2] if best else None
