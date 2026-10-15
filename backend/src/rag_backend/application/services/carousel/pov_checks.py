"""Deterministic "Ponto de Vista" text checks (AE-0375, growth plan 16.3 C).

Pure functions over visible copy: the hook word count, first-person presence,
and whether the thesis shows up on slides 1-2. They never call a model.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from rag_backend.domain.constants.content_mode import HOOK_MAX_WORDS

# PT first-person singular markers (growth plan 16.3 C: ">=3 slides in first
# person"). Whole words, accents folded.
FIRST_PERSON_MARKERS: frozenset[str] = frozenset({
    "eu",
    "meu",
    "minha",
    "meus",
    "minhas",
    "comigo",
    "me",
})
MIN_FIRST_PERSON_SLIDES = 3
# Words too common to show the thesis is present (folded, >= 4 letters).
THESIS_STOPWORDS: frozenset[str] = frozenset({
    "para",
    "como",
    "mais",
    "isso",
    "esse",
    "essa",
    "este",
    "esta",
    "voce",
    "ainda",
    "quem",
    "pelo",
    "pela",
    "porque",
    "quando",
    "sobre",
    "muito",
    "sempre",
    "nunca",
    "todo",
    "toda",
    "todos",
    "tudo",
    "nada",
    "seu",
    "sua",
    "with",
    "that",
    "this",
    "from",
})
MIN_THESIS_WORD_LENGTH = 4
_WORD = re.compile(r"[a-z0-9]+")


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def words(text: str) -> list[str]:
    """Lower-cased, accent-folded words of ``text`` (markup-insensitive)."""
    return _WORD.findall(_fold(re.sub(r"<[^>]+>", " ", text)))


def hook_too_long(heading: str) -> bool:
    """True when a hook heading has more than ``HOOK_MAX_WORDS`` words."""
    return len(heading.split()) > HOOK_MAX_WORDS


def is_first_person(text: str) -> bool:
    """True when ``text`` contains a PT first-person marker."""
    return any(word in FIRST_PERSON_MARKERS for word in words(text))


def first_person_slide_count(slide_texts: Iterable[str]) -> int:
    """How many slides speak in the first person."""
    return sum(1 for text in slide_texts if is_first_person(text))


def thesis_keywords(thesis: str) -> frozenset[str]:
    """The thesis' content words (folded, >= 4 letters, not stopwords)."""
    return frozenset(
        word
        for word in words(thesis)
        if len(word) >= MIN_THESIS_WORD_LENGTH and word not in THESIS_STOPWORDS
    )


def thesis_appears_early(early_texts: Iterable[str], thesis: str) -> bool:
    """True when a thesis keyword is on slides 1-2 (or the thesis has none)."""
    keywords = thesis_keywords(thesis)
    if not keywords:
        return True
    present = {word for text in early_texts for word in words(text)}
    return bool(keywords & present)


__all__ = [
    "FIRST_PERSON_MARKERS",
    "MIN_FIRST_PERSON_SLIDES",
    "first_person_slide_count",
    "hook_too_long",
    "is_first_person",
    "thesis_appears_early",
    "thesis_keywords",
    "words",
]
