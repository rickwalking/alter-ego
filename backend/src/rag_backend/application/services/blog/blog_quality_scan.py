"""Deterministic half of the blog quality gate (AE-0425, ADR-0025).

No model is involved here, so every finding is reproducible:

* :func:`scan_sections` — sentences restated across the article (F-03),
  sentences copied verbatim from a source note, and banned stock phrases
  (the list is data, ``domain/constants/blog_voice.py``).
* :func:`strip_source_leaks` — drops any PT sentence that is a verbatim copy of
  the (English) research findings, so a research intro can never leak into the
  Portuguese body (F-05 class). The EN translation is not touched.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

import structlog

from rag_backend.domain.constants.blog_generation import LANGUAGE_EN, LOG_ENGLISH_IN_PT
from rag_backend.domain.constants.blog_voice import (
    BANNED_PHRASES_EN,
    BANNED_PHRASES_PT,
    ENGLISH_DOMINANCE,
    ENGLISH_FUNCTION_WORDS,
    ENGLISH_MIN_HITS,
    PORTUGUESE_FUNCTION_WORDS,
    REPEATED_SENTENCE_MIN_CHARS,
)
from rag_backend.domain.models.blog_generation import DraftSection, QualityFindings

logger = structlog.get_logger(__name__)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_MARKDOWN_NOISE = re.compile(r"[*_`#>\[\]]")
_WHITESPACE = re.compile(r"\s+")
_WORD = re.compile(r"[a-zà-ÿ']+")
_TRAILING_PUNCTUATION = ".!?;:,\"'”“ "


@dataclass(frozen=True)
class ScanInput:
    """One language of the article plus the source notes it must not copy."""

    language: str
    sections: tuple[DraftSection, ...]
    notes: tuple[str, ...] = ()


def normalize_sentence(sentence: str) -> str:
    """Lowercase, markdown-free, whitespace-collapsed, no trailing punctuation."""
    cleaned = _MARKDOWN_NOISE.sub("", sentence)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip().lower()
    return cleaned.rstrip(_TRAILING_PUNCTUATION)


def split_sentences(text: str) -> list[str]:
    """The non-blank sentences of ``text`` (paragraph breaks also split)."""
    sentences: list[str] = []
    for paragraph in _PARAGRAPH_SPLIT.split(text):
        sentences.extend(
            part.strip() for part in _SENTENCE_SPLIT.split(paragraph) if part.strip()
        )
    return sentences


def _significant(sentences: Iterable[str]) -> list[tuple[str, str]]:
    pairs = ((sentence, normalize_sentence(sentence)) for sentence in sentences)
    return [pair for pair in pairs if len(pair[1]) >= REPEATED_SENTENCE_MIN_CHARS]


def _repeated(sections: tuple[DraftSection, ...]) -> list[str]:
    seen: dict[str, str] = {}
    repeated: dict[str, str] = {}
    for section in sections:
        for original, key in _significant(split_sentences(section.body_md)):
            if key in seen and key not in repeated:
                repeated[key] = seen[key]
            seen.setdefault(key, original)
    return list(repeated.values())


def _copied_from_notes(scan: ScanInput) -> list[str]:
    note_keys = {
        key: original
        for note in scan.notes
        for original, key in _significant(split_sentences(note))
    }
    copied: dict[str, str] = {}
    for section in scan.sections:
        for _original, key in _significant(split_sentences(section.body_md)):
            if key in note_keys:
                copied.setdefault(key, note_keys[key])
    return list(copied.values())


def _banned_phrases(scan: ScanInput) -> list[str]:
    phrases = BANNED_PHRASES_EN if scan.language == LANGUAGE_EN else BANNED_PHRASES_PT
    text = "\n".join(
        f"{section.heading or ''}\n{section.body_md}" for section in scan.sections
    ).lower()
    return [
        phrase
        for phrase in phrases
        if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None
    ]


def reads_as_english(text: str) -> bool:
    """English function words dominate (cheap; no model, no dependency)."""
    words = _WORD.findall(text.lower())
    english = sum(word in ENGLISH_FUNCTION_WORDS for word in words)
    portuguese = sum(word in PORTUGUESE_FUNCTION_WORDS for word in words)
    return english >= ENGLISH_MIN_HITS and english > ENGLISH_DOMINANCE * portuguese


def _english_sections(scan: ScanInput) -> list[str]:
    if scan.language == LANGUAGE_EN:
        return []
    return [
        section.heading or f"#{index + 1}"
        for index, section in enumerate(scan.sections)
        if reads_as_english(section.body_md)
    ]


def scan_sections(scan: ScanInput) -> QualityFindings:
    """Repetition (incl. verbatim note copies), banned phrases and, for PT,
    sections that read as English."""
    repeated = _repeated(scan.sections)
    for sentence in _copied_from_notes(scan):
        if sentence not in repeated:
            repeated.append(sentence)
    english = _english_sections(scan)
    if english:
        logger.warning(LOG_ENGLISH_IN_PT, sections=english)
    return QualityFindings(
        repeated_sentences=tuple(repeated),
        banned_phrases=tuple(_banned_phrases(scan)),
        english_sections=tuple(english),
    )


def _strip_paragraph(paragraph: str, leaked: frozenset[str]) -> str:
    kept = [
        sentence
        for sentence in _SENTENCE_SPLIT.split(paragraph.strip())
        if sentence.strip() and normalize_sentence(sentence) not in leaked
    ]
    return " ".join(kept)


def _strip_body(body: str, leaked: frozenset[str]) -> str:
    paragraphs = (
        _strip_paragraph(paragraph, leaked)
        for paragraph in _PARAGRAPH_SPLIT.split(body)
    )
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def strip_source_leaks(
    sections: tuple[DraftSection, ...], research: tuple[str, ...]
) -> tuple[tuple[DraftSection, ...], int]:
    """Drop PT sentences copied verbatim from the research; (sections, dropped)."""
    leaked = frozenset(
        key
        for text in research
        for _original, key in _significant(split_sentences(text))
    )
    if not leaked:
        return sections, 0
    stripped = tuple(
        DraftSection(
            heading=section.heading, body_md=_strip_body(section.body_md, leaked)
        )
        for section in sections
    )
    dropped = sum(
        len(split_sentences(before.body_md)) - len(split_sentences(after.body_md))
        for before, after in zip(sections, stripped, strict=True)
    )
    return stripped, dropped


__all__ = [
    "ScanInput",
    "normalize_sentence",
    "reads_as_english",
    "scan_sections",
    "split_sentences",
    "strip_source_leaks",
]
