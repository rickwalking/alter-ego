"""Deterministic presentation copy repair for one bounded attempt per locale."""

from __future__ import annotations

import re
from collections.abc import Mapping

from rag_backend.domain.constants.carousel import LANGUAGE_EN
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_DASH_PUNCTUATION_FORBIDDEN,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
    VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation

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


def _repair_text_field(
    payload: dict[str, object],
    field: str,
    violations: set[str],
    locale: str,
) -> None:
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
    _repair_text_field(repaired, "heading", codes, locale)
    _repair_text_field(repaired, "body", codes, locale)
    return repaired


__all__ = ["deterministic_repair_slide_payload"]
