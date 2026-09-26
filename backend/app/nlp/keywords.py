"""Keyword and key-phrase extraction.

Combines two unsupervised techniques:

* **RAKE** (Rapid Automatic Keyword Extraction) finds multi-word candidate
  phrases delimited by stop words and punctuation and scores them by word
  degree / frequency.
* **TF-IDF** scores single terms against corpus document frequencies (when
  available), so words that are common across the whole index rank lower.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Callable

from .text import is_stop_word, normalize, stem

_SENTENCE_SPLIT_RE = re.compile(r"[.!?,;:\t\n\r()\[\]{}\"“”]+|\s[-–—]\s")
_WORD_RE = re.compile(r"[a-z0-9]+(?:['’.\-+#][a-z0-9+#]+)*[+#]*")


@dataclass(frozen=True)
class Keyword:
    text: str
    score: float

    def to_dict(self) -> dict:
        return {"text": self.text, "score": round(self.score, 4)}


def _content_runs(text: str) -> list[list[str]]:
    """Maximal runs of content words, split at stop words, numbers and punctuation."""
    runs: list[list[str]] = []
    for fragment in _SENTENCE_SPLIT_RE.split(normalize(text)):
        current: list[str] = []
        for word in (m.group().strip(".-") for m in _WORD_RE.finditer(fragment)):
            if not word or is_stop_word(word) or len(word) < 2 or word.isdigit():
                if current:
                    runs.append(current)
                current = []
            else:
                current.append(word)
        if current:
            runs.append(current)
    return runs


def rake(text: str, max_words: int = 3) -> dict[str, float]:
    """Return RAKE-style scores for candidate n-grams, keyed by the phrase text.

    Word scores follow RAKE (degree / frequency over the content-word runs).
    Candidates are all n-grams up to ``max_words`` inside a run, so a repeated
    sub-phrase ("inverted index") can beat a longer phrase seen only once.
    """
    runs = _content_runs(text)
    frequency: Counter[str] = Counter()
    degree: Counter[str] = Counter()
    for run in runs:
        for word in run:
            frequency[word] += 1
            degree[word] += min(len(run), max_words) - 1
    word_score = {w: (degree[w] + frequency[w]) / frequency[w] for w in frequency}

    ngram_counts: Counter[tuple[str, ...]] = Counter()
    for run in runs:
        for n in range(1, min(max_words, len(run)) + 1):
            for i in range(len(run) - n + 1):
                ngram_counts[tuple(run[i : i + n])] += 1

    whole_runs = {tuple(run) for run in runs if len(run) <= max_words}
    scores: dict[str, float] = {}
    for ngram, count in ngram_counts.items():
        if len(ngram) > 1 and count == 1 and ngram not in whole_runs:
            continue  # arbitrary slices of long runs are rarely meaningful phrases
        mean_word = sum(word_score[w] for w in ngram) / len(ngram)
        scores[" ".join(ngram)] = mean_word * (1 + 0.5 * (len(ngram) - 1)) * (1 + math.log(count))
    return scores


def extract_keywords(
    text: str,
    top_k: int = 10,
    doc_freq: Callable[[str], int] | None = None,
    total_docs: int = 0,
) -> list[Keyword]:
    """Extract the ``top_k`` most characteristic keywords / phrases from ``text``.

    ``doc_freq`` maps a stemmed term to the number of indexed documents that
    contain it; when supplied, it turns term frequency into TF-IDF.
    """
    runs = _content_runs(text)
    if not runs:
        return []

    words = [w for run in runs for w in run]
    tf = Counter(stem(w) for w in words)
    surface_for: dict[str, Counter[str]] = defaultdict(Counter)
    for w in words:
        surface_for[stem(w)][w] += 1
    max_tf = max(tf.values())

    def idf(term: str) -> float:
        if doc_freq is None or total_docs <= 0:
            return 1.0
        return math.log(1 + (total_docs + 1) / (doc_freq(term) + 1))

    term_scores = {t: (0.5 + 0.5 * c / max_tf) * idf(t) for t, c in tf.items()}

    rake_scores = rake(text)
    max_rake = max(rake_scores.values()) if rake_scores else 1.0

    candidates: dict[str, float] = {}
    for phrase_text, rake_score in rake_scores.items():
        stems = [stem(w) for w in phrase_text.split()]
        tfidf = sum(term_scores.get(s, 0) for s in stems) / len(stems)
        # Blend normalized RAKE with average TF-IDF of the phrase's words.
        score = 0.5 * (rake_score / max_rake) + 0.5 * tfidf / max(term_scores.values())
        if len(stems) == 1:
            # Represent single words by their most common surface form.
            phrase_text = surface_for[stems[0]].most_common(1)[0][0]
        candidates[phrase_text] = max(candidates.get(phrase_text, 0.0), score)

    ranked = sorted(candidates.items(), key=lambda kv: (-kv[1], kv[0]))
    selected: list[Keyword] = []
    selected_stems: list[set[str]] = []
    for phrase_text, score in ranked:
        stems = {stem(w) for w in phrase_text.split()}
        # Skip candidates that mostly repeat an already selected keyword.
        if any(len(stems & chosen) / len(stems) > 0.5 for chosen in selected_stems):
            continue
        selected.append(Keyword(phrase_text, score))
        selected_stems.append(stems)
        if len(selected) >= top_k:
            break
    return selected
