"""Deterministic presentation copy repair for one bounded attempt per locale."""

from __future__ import annotations

import re
from collections.abc import Mapping, Set
from typing import TypedDict

from rag_backend.domain.constants.carousel import LANGUAGE_EN
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_DASH_PUNCTUATION_FORBIDDEN,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
    VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation


class RepairFieldCommand(TypedDict):
    """Parameters for repairing a single text field."""

    payload: dict[str, object]
    field: str
    violations: Set[str]
    locale: str


_EM_DASH = "\u2014"
_EN_DASH = "\u2013"
_EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F600-\U0001F64F]",
    flags=re.UNICODE,
)


def _strip_visible_emoji(text: str) -> str:
    return _EMOJI_PATTERN.sub("", text).strip()


def _replace_forbidden_dashes(text: str) -> str:
    return text.replace(_EM_DASH, "-").replace(_EN_DASH, "-")


def _repair_heading_sentence_case_en(heading: str) -> str:
    chars = list(heading)
    for index, char in enumerate(chars):
        if char.isalpha():
            chars[index] = char.upper()
            break
    return "".join(chars)


# Matches a single HTML tag (e.g. ``<b>``, ``</span>``, ``<br/>``) so the
# sentence-case repair can skip over markup and uppercase the first *visible*
# letter instead of a character inside a tag name.
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def repair_text_sentence_case_en(text: str) -> str:
    """Uppercase the first visible letter of EN render-source copy.

    Skips leading HTML tags so headings/bodies wrapped in markup
    (e.g. ``<b>insight</b>``) are sentence-cased on the first visible
    letter rather than a character inside the tag. Idempotent: already
    sentence-cased text is returned unchanged.
    """
    if not text:
        return text
    index = 0
    length = len(text)
    while index < length:
        tag_match = _HTML_TAG_PATTERN.match(text, index)
        if tag_match is not None:
            index = tag_match.end()
            continue
        char = text[index]
        if char.isalpha():
            if char.islower():
                return text[:index] + char.upper() + text[index + 1 :]
            return text
        index += 1
    return text


def _repair_text_field(
    command: RepairFieldCommand,
) -> None:
    payload = command["payload"]
    field = command["field"]
    violations = command["violations"]
    locale = command["locale"]
    raw = payload.get(field)
    if not isinstance(raw, str) or not raw:
        return
    repaired = raw
    if VIOLATION_VISIBLE_EMOJI_FORBIDDEN in violations:
        repaired = _strip_visible_emoji(repaired)
    if VIOLATION_DASH_PUNCTUATION_FORBIDDEN in violations:
        repaired = _replace_forbidden_dashes(repaired)
    if (
        field == "heading"
        and locale == LANGUAGE_EN
        and VIOLATION_HEADING_NOT_SENTENCE_CASE_EN in violations
    ):
        repaired = _repair_heading_sentence_case_en(repaired)
    payload[field] = repaired


def deterministic_repair_slide_payload(
    payload: Mapping[str, object],
    violations: tuple[SlideValidationViolation, ...],
    locale: str,
) -> dict[str, object]:
    """Apply deterministic repairs for supported violation codes."""
    repaired = dict(payload)
    codes = {violation.code for violation in violations}
    _repair_text_field(
        RepairFieldCommand(
            payload=repaired, field="heading", violations=codes, locale=locale
        )
    )
    _repair_text_field(
        RepairFieldCommand(
            payload=repaired, field="body", violations=codes, locale=locale
        )
    )
    return repaired


__all__ = [
    "deterministic_repair_slide_payload",
    "repair_text_sentence_case_en",
]
