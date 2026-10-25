"""Whether a checklist item body stops mid-sentence.

Item bodies are often fragments with no closing punctuation ("Revisão
automática de PRs"), so only a clear cut-off counts:

- an open ending: an ellipsis or a dangling ``,:;-``;
- a last word that is a function word ("O agente conduz a", "The agent does
  not", "Não é"), lowercase, or the whole body ("This");
- a body written as sentences whose last one, three words or more, has no
  closing punctuation ("Eu vejo diferente: funcionário tem").

A sentence break is ``.``/``?``/``!`` followed by whitespace and an uppercase
letter, never after a known abbreviation, so "Node.js", "Grok 3.5", "GPT-4.1",
"2.5x", "e.g. Claude" and "Funciona? Sim" are not cut-offs.
"""

from __future__ import annotations

import re

from rag_backend.application.services.carousel.copy_hygiene_text import (
    open_ending_detail,
    plain_text,
)

ITEM_TRUNCATION_NO_CLOSE = "no closing punctuation"
ITEM_TRUNCATION_ENDS_ON = 'ends on "{word}"'
_MIN_LAST_SENTENCE_WORDS = 3
_TERMINAL_PUNCTUATION = ".!?"
_TRAILING_CLOSERS = "\"'\u201d\u2019\u00bb)]*"
_WORD_PATTERN = re.compile(r"[^\W\d_]+|\d+")
_SENTENCE_BREAK = re.compile(r"(\S*)[.!?]\s+(?=[A-ZÀ-ÖØ-Þ])")
_ABBREVIATIONS: frozenset[str] = frozenset({
    "e.g",
    "i.e",
    "etc",
    "vs",
    "ex",
    "p.ex",
    "obs",
    "aprox",
    "approx",
    "sr",
    "sra",
    "dr",
    "dra",
    "prof",
    "mr",
    "mrs",
    "ms",
})
_FUNCTION_WORDS: frozenset[str] = frozenset({
    "a",
    "o",
    "as",
    "os",
    "um",
    "uma",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "e",
    "ou",
    "mas",
    "que",
    "com",
    "sem",
    "para",
    "por",
    "em",
    "no",
    "na",
    "nos",
    "nas",
    "não",
    "é",
    "se",
    "como",
    "the",
    "an",
    "and",
    "or",
    "but",
    "of",
    "to",
    "for",
    "with",
    "in",
    "on",
    "at",
    "not",
    "is",
    "are",
    "this",
    "that",
    "it",
    "its",
})


def _last_sentence(text: str) -> str | None:
    """The text after the last real sentence break, or None when there is none."""
    last_end: int | None = None
    for match in _SENTENCE_BREAK.finditer(text):
        token = match.group(1).casefold().rstrip(_TERMINAL_PUNCTUATION)
        if token in _ABBREVIATIONS:
            continue
        last_end = match.end()
    return None if last_end is None else text[last_end:]


def _dangling_word(closed: str) -> str:
    words = _WORD_PATTERN.findall(closed)
    if not words:
        return ""
    last = words[-1]
    lowered = last.casefold()
    if lowered not in _FUNCTION_WORDS:
        return ""
    return lowered if last == lowered or len(words) == 1 else ""


def _unfinished_sentence(closed: str) -> str:
    last = _last_sentence(closed)
    if last is None or len(_WORD_PATTERN.findall(last)) < _MIN_LAST_SENTENCE_WORDS:
        return ""
    return ITEM_TRUNCATION_NO_CLOSE


def item_truncation_detail(text: str) -> str:
    """Why a checklist item body reads as cut off, or empty when it does not."""
    plain = plain_text(text)
    if not plain:
        return ""
    open_ending = open_ending_detail(plain)
    if open_ending:
        return open_ending
    closed = plain.rstrip(_TRAILING_CLOSERS)
    if closed and closed[-1] in _TERMINAL_PUNCTUATION:
        return ""
    dangling = _dangling_word(closed)
    if dangling:
        return ITEM_TRUNCATION_ENDS_ON.format(word=dangling)
    return _unfinished_sentence(closed)


__all__ = ["item_truncation_detail"]
