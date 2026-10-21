"""Language and topic filter for web-research hits.

QA run 2026-10-16: the topic "[QA 2026-10-16] Agentes de código em times
pequenos" was searched as-is, the search keyed on "QA", and three Russian
pages (a YouTube stream, QA salaries in Russia, an FT note on sulfur) became
research findings, then outline claims, then Russian paragraphs in the blog.

- :func:`search_query_for` drops bracketed tags ("[QA 2026-10-16]") and
  emoji from the topic before it is searched.
- :func:`hit_rejection` keeps only Portuguese/English hits that share a
  keyword with the query. Owner-provided sources are never filtered.

Pure functions, no I/O.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rag_backend.domain.constants.carousel_autofix import (
    ENGLISH_MARKERS,
    PORTUGUESE_MARKERS,
)
from rag_backend.domain.constants.research_enrichment import (
    FILTER_REASON_LANGUAGE,
    FILTER_REASON_OFF_TOPIC,
    KEYWORD_STEM_CHARS,
    MIN_KEYWORD_CHARS,
    MIN_LANGUAGE_FILTER_WORDS,
    MIN_LATIN_LETTER_RATIO,
)

_BRACKETED_TAG = re.compile(r"\[[^\]]*\]")
_WORD = re.compile(r"[^\W\d_]+")
_LATIN = "LATIN"
_SYMBOL_CATEGORIES = frozenset({"So", "Sk", "Cs", "Co"})
_STOPWORDS = PORTUGUESE_MARKERS | ENGLISH_MARKERS


@dataclass(frozen=True)
class ResearchHit:
    """The visible text of one search hit (title + snippet)."""

    title: str
    snippet: str

    @property
    def text(self) -> str:
        """Title and snippet as one string."""
        return f"{self.title} {self.snippet}"


def search_query_for(topic: str) -> str:
    """The topic without bracketed tags and emoji (falls back to the topic)."""
    without_tags = _BRACKETED_TAG.sub(" ", topic)
    visible = "".join(
        char
        for char in without_tags
        if unicodedata.category(char) not in _SYMBOL_CATEGORIES
    )
    query = " ".join(visible.split())
    return query or topic.strip()


def _fold(word: str) -> str:
    decomposed = unicodedata.normalize("NFKD", word.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _stems(text: str) -> set[str]:
    return {
        _fold(word)[:KEYWORD_STEM_CHARS]
        for word in _WORD.findall(text)
        if len(word) >= MIN_KEYWORD_CHARS and word.casefold() not in _STOPWORDS
    }


def _is_portuguese_or_english(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return True
    latin = sum(1 for char in letters if unicodedata.name(char, "").startswith(_LATIN))
    if latin / len(letters) < MIN_LATIN_LETTER_RATIO:
        return False
    words = [word.casefold() for word in _WORD.findall(text)]
    if len(words) < MIN_LANGUAGE_FILTER_WORDS:
        return True
    return any(word in _STOPWORDS for word in words)


def hit_rejection(hit: ResearchHit, query: str) -> str | None:
    """Why a search hit is rejected (language / off topic), or None to keep it."""
    if not _is_portuguese_or_english(hit.text):
        return FILTER_REASON_LANGUAGE
    keywords = _stems(query)
    if keywords and not keywords & _stems(hit.text):
        return FILTER_REASON_OFF_TOPIC
    return None


__all__ = ["ResearchHit", "hit_rejection", "search_query_for"]
