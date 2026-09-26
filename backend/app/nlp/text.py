"""Core text analysis: normalization, tokenization, stop words and stemming.

The same analyzer is used for indexing documents and for processing queries so
that both sides of the inverted index agree on what a "term" is.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

import snowballstemmer

STOP_WORDS: frozenset[str] = frozenset(
    """
    a about above after again against all am an and any are aren't as at be because been before
    being below between both but by can can't cannot could couldn't did didn't do does doesn't doing
    don't down during each few for from further had hadn't has hasn't have haven't having he he'd
    he'll he's her here here's hers herself him himself his how how's i i'd i'll i'm i've if in into
    is isn't it it's its itself let's me more most mustn't my myself no nor not of off on once only
    or other ought our ours ourselves out over own same shan't she she'd she'll she's should
    shouldn't so some such than that that's the their theirs them themselves then there there's
    these they they'd they'll they're they've this those through to too under until up very was
    wasn't we we'd we'll we're we've were weren't what what's when when's where where's which while
    who who's whom why why's will with won't would wouldn't you you'd you'll you're you've your
    yours yourself yourselves also just may might must shall us get got via etc e.g i.e
    without within upon among since though although however instead often every many much
    even still yet whether else either neither rather per another several
    """.split()
)

# Matches words, keeping inner apostrophes/hyphens/dots ("don't", "e-mail", "node.js")
# and alphanumeric tokens such as "python3" or "2024".
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:['’.\-+#][a-z0-9+#]+)*[+#]*")

_stemmer = snowballstemmer.stemmer("english")


@dataclass(frozen=True)
class Token:
    """A single token produced by the analyzer."""

    surface: str  # lower-cased word as it appeared in the text
    term: str  # stemmed form used in the index
    position: int  # position among all tokens (stop words included)
    start: int  # character offset in the original text
    end: int


def normalize(text: str) -> str:
    """Lower-case and strip accents so "Café" and "cafe" match."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


@lru_cache(maxsize=50_000)
def stem(word: str) -> str:
    word = word.replace("’", "'")
    if "'" in word:
        word = word.split("'", 1)[0] or word
    if any(ch.isdigit() for ch in word) or any(ch in word for ch in ".+#-"):
        return word  # identifiers such as "node.js", "c++", "python3" stay intact
    return _stemmer.stemWord(word)


def is_stop_word(word: str) -> bool:
    return word.replace("’", "'") in STOP_WORDS


def tokenize(text: str) -> list[Token]:
    """Split text into tokens, skipping stop words but preserving positions.

    Positions count stop words too, so that phrase queries like "state of the art"
    still require the words to be adjacent in the original text.
    """
    normalized = normalize(text)
    tokens: list[Token] = []
    for position, match in enumerate(_TOKEN_RE.finditer(normalized)):
        surface = match.group().strip(".-")
        if not surface or is_stop_word(surface) or (len(surface) == 1 and not surface.isdigit()):
            continue
        tokens.append(Token(surface, stem(surface), position, match.start(), match.end()))
    return tokens


def raw_words(text: str) -> list[str]:
    """All lower-cased words in the text, including stop words."""
    return [m.group().strip(".-") for m in _TOKEN_RE.finditer(normalize(text)) if m.group().strip(".-")]


def analyze(text: str) -> list[str]:
    """Return the list of index terms (stems) for a piece of text."""
    return [token.term for token in tokenize(text)]
