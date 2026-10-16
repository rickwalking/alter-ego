"""Proper-noun vocabulary of one carousel for the owner autofix (AE-0367).

Prod carousel 8e350d6e lowercased "Argon" in its copy while the outline kept
it capitalized. The fix restores capitals from the carousel's own vocabulary:
a word written capitalized in the MIDDLE of a sentence (never its first word)
in a sentence-case source (outline titles and key points, the PT/EN copy) is a
proper noun, unless a trusted source (outline, research) also writes it
lowercase mid-sentence. A multi-word name ("Claude Code", "Grok Bot") is
learned whole, never its last word alone (AE-0401). Research titles are often
Title Case, so from those
only distinctive tokens are trusted ("OpenAI", "GPT-5"). The constants list and
the policy's configured proper nouns are always included.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from rag_backend.domain.constants.carousel_autofix import (
    ACRONYM_MAX_LENGTH,
    ENGLISH_MARKERS,
    KNOWN_PROPER_NOUNS,
    PORTUGUESE_MARKERS,
    TITLE_CASE_MIN_WORD_LENGTH,
    TITLE_CASE_SHARE,
    VOCABULARY_MIN_TOKEN_LENGTH,
)

_TAG_PATTERN = re.compile(r"<[^>]+>")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?:;])\s+|\n+")
_TOKEN_PATTERN = re.compile(r"[^\W_](?:[\w\-]*[^\W_])?")
_COMMON = PORTUGUESE_MARKERS | ENGLISH_MARKERS


@dataclass(frozen=True)
class VocabularySources:
    """Texts one carousel provides. ``trusted`` = outline + research copy."""

    trusted: tuple[str, ...] = ()
    copy: tuple[str, ...] = ()
    titles: tuple[str, ...] = ()
    configured: tuple[str, ...] = ()


@dataclass
class _Tally:
    capitalized: Counter[str]
    lowercase_trusted: set[str]


def _sentences(text: str) -> list[str]:
    plain = _TAG_PATTERN.sub(" ", text)
    return [part for part in _SENTENCE_SPLIT.split(plain) if part.strip()]


def _mid_tokens(sentence: str) -> list[str]:
    return _TOKEN_PATTERN.findall(sentence)[1:]


def _is_distinctive(token: str) -> bool:
    """Inner capital or a digit: "OpenAI", "iPhone", "GPT-5"."""
    inner_upper = any(char.isupper() for char in token[1:]) and any(
        char.islower() for char in token
    )
    has_digit = any(char.isdigit() for char in token)
    return (inner_upper or has_digit) and any(char.isalpha() for char in token)


def _is_capitalized(token: str) -> bool:
    """ "Argon" or a short acronym ("API"); a long all-caps word is emphasis."""
    if not token[0].isupper():
        return False
    return token != token.upper() or len(token) <= ACRONYM_MAX_LENGTH


def _is_candidate(token: str) -> bool:
    if len(token) < VOCABULARY_MIN_TOKEN_LENGTH or token.casefold() in _COMMON:
        return False
    return _is_capitalized(token) or _is_distinctive(token)


def _runs(sentence: str) -> list[tuple[int, list[str]]]:
    """(first token position, tokens) of each run of adjacent candidate tokens.

    Tokens separated only by whitespace are one name ("Claude Code", "Grok
    Bot"); a comma or any other character ends the run.
    """
    runs: list[tuple[int, list[str]]] = []
    previous_end = -1
    for position, match in enumerate(_TOKEN_PATTERN.finditer(sentence)):
        token = match.group(0)
        if not _is_candidate(token):
            previous_end = -1
            continue
        gap = sentence[previous_end : match.start()] if previous_end >= 0 else "x"
        if runs and not gap.strip():
            runs[-1][1].append(token)
        else:
            runs.append((position, [token]))
        previous_end = match.end()
    return runs


def _count_sentence_case(text: str, tally: _Tally, *, trusted: bool) -> None:
    """Count capitalized mid-sentence names; a multi-word name counts whole.

    AE-0401: "Claude Code" used to teach "Code" alone, so "the code" in EN was
    reported as a lowercased proper noun. Only the full phrase is learned.
    """
    for sentence in _sentences(text):
        for position, tokens in _runs(sentence):
            if len(tokens) > 1:
                tally.capitalized[" ".join(tokens)] += 1
            elif position > 0:
                tally.capitalized[tokens[0]] += 1
        if trusted:
            tally.lowercase_trusted.update(
                token
                for token in _mid_tokens(sentence)
                if token == token.lower() and not _is_candidate(token)
            )


def _is_title_case(title: str) -> bool:
    words = [
        word
        for word in _TOKEN_PATTERN.findall(title)
        if len(word) >= TITLE_CASE_MIN_WORD_LENGTH
    ]
    if not words:
        return False
    capitalized = sum(1 for word in words if word[0].isupper())
    return capitalized / len(words) >= TITLE_CASE_SHARE


def _count_title(title: str, tally: _Tally) -> None:
    if not _is_title_case(title):
        _count_sentence_case(title, tally, trusted=True)
        return
    for token in _TOKEN_PATTERN.findall(_TAG_PATTERN.sub(" ", title)):
        if _is_distinctive(token) and _is_candidate(token):
            tally.capitalized[token] += 1


def _canonical(tally: _Tally) -> dict[str, str]:
    """One spelling per word (the most frequent), minus trusted lowercase words."""
    chosen: dict[str, tuple[int, str]] = {}
    for token, count in tally.capitalized.items():
        key = token.casefold()
        if key in tally.lowercase_trusted:
            continue
        best = chosen.get(key)
        if best is None or count > best[0]:
            chosen[key] = (count, token)
    return {key: token for key, (_, token) in chosen.items()}


def build_vocabulary(sources: VocabularySources) -> tuple[str, ...]:
    """Canonical proper nouns of the carousel, longest first."""
    tally = _Tally(capitalized=Counter(), lowercase_trusted=set())
    for text in sources.trusted:
        _count_sentence_case(text, tally, trusted=True)
    for text in sources.copy:
        _count_sentence_case(text, tally, trusted=False)
    for title in sources.titles:
        _count_title(title, tally)
    nouns = _canonical(tally)
    for noun in (*KNOWN_PROPER_NOUNS, *sources.configured):
        nouns[noun.casefold()] = noun
    return tuple(sorted(nouns.values(), key=lambda noun: (-len(noun), noun)))


__all__ = ["VocabularySources", "build_vocabulary"]
