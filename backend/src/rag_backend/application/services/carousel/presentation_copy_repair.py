"""Deterministic presentation copy repair for one bounded attempt per locale."""

from __future__ import annotations

import re
from collections.abc import Mapping, Set
from typing import TypedDict

from rag_backend.application.services.carousel.presentation_policy import (
    CarouselPresentationPolicy,
)
from rag_backend.application.services.carousel.presentation_validation_fields import (
    body_budget_for_slide_type,
)
from rag_backend.application.services.carousel.slide_scaffold_recovery import (
    recover_scaffold_body,
    strip_scaffold_labels,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_BODY_TOO_LONG,
    VIOLATION_DASH_PUNCTUATION_FORBIDDEN,
    VIOLATION_DRAFTING_SCAFFOLD_PRESENT,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
    VIOLATION_HEADING_REPEATED_IN_BODY,
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


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_ELLIPSIS = "…"
# Reserve headroom in the word-boundary fallback so the trailing ellipsis (and a
# rstrip of trailing punctuation) can never push the result back over budget.
_FALLBACK_HEADROOM = 1


def _balance_inline_markup(text: str) -> str:
    """Close inline markup left unbalanced by a cut (no dangling ** or <strong>)."""
    if text.count("**") % 2 == 1:
        cut = text.rfind("**")
        text = (text[:cut] + text[cut + 2 :]).rstrip()
    for open_tag, close_tag in (("<strong>", "</strong>"), ("<b>", "</b>")):
        unclosed = text.count(open_tag) - text.count(close_tag)
        if unclosed > 0:
            text += close_tag * unclosed
    return text


def _trim_body_to_budget(text: str, max_characters: int) -> str:
    """Shorten body copy to fit ``max_characters`` without producing nonsense.

    Prefers keeping whole sentences (complete, on-topic, balanced markup). Only
    when a single sentence already exceeds the budget does it fall back to a
    word-boundary cut with an ellipsis. Never cuts mid-word; never exceeds budget.
    """
    text = text.strip()
    if len(text) <= max_characters:
        return text
    kept = ""
    for sentence in _SENTENCE_BOUNDARY.split(text):
        candidate = f"{kept} {sentence}".strip() if kept else sentence.strip()
        if len(candidate) <= max_characters:
            kept = candidate
        else:
            break
    if kept:
        return _balance_inline_markup(kept)
    # No whole sentence fits: keep whole words up to the budget, drop inline
    # markup (so nothing is left dangling) and mark the cut with an ellipsis.
    limit = max_characters - _FALLBACK_HEADROOM
    truncated = ""
    for word in text.split():
        candidate = f"{truncated} {word}".strip() if truncated else word
        if len(candidate) <= limit:
            truncated = candidate
        else:
            break
    plain = re.sub(r"<[^>]+>", "", truncated).replace("**", "").rstrip(" \t,;:-")
    result = (plain + _ELLIPSIS) if plain else text[:max_characters]
    return result[:max_characters]


def _strip_heading_from_body(body: str, heading: str) -> str:
    """Remove the heading text repeated inside the body (case-insensitive).

    Strips both the raw heading and a markup-free variant, then tidies the
    leftover punctuation/whitespace so the body reads cleanly.
    """
    needles = {
        heading.strip(),
        re.sub(r"<[^>]+>|[*_`]", "", heading).strip(),
    }
    cleaned = body
    for needle in needles:
        if needle:
            cleaned = re.compile(re.escape(needle), re.IGNORECASE).sub(" ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" \t\n.,:;-")
    return cleaned or body


def _repair_scaffold_fields(
    payload: dict[str, object],
    codes: Set[str],
    locale: str,
) -> None:
    """Strip drafting-scaffold labels from visible copy (AE-0309)."""
    if VIOLATION_DRAFTING_SCAFFOLD_PRESENT not in codes:
        return
    body = payload.get("body")
    if isinstance(body, str) and body:
        payload["body"] = recover_scaffold_body(body, locale)
    heading = payload.get("heading")
    if isinstance(heading, str) and heading:
        payload["heading"] = strip_scaffold_labels(heading) or heading


def deterministic_repair_slide_payload(
    payload: Mapping[str, object],
    violations: tuple[SlideValidationViolation, ...],
    locale: str,
) -> dict[str, object]:
    """Apply deterministic markup/case/scaffold repairs for supported codes."""
    repaired = dict(payload)
    codes = {violation.code for violation in violations}
    _repair_scaffold_fields(repaired, codes, locale)
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


def repair_body_length_and_heading(
    payload: Mapping[str, object],
    violations: tuple[SlideValidationViolation, ...],
    policy: CarouselPresentationPolicy,
) -> dict[str, object]:
    """Strip a repeated heading then trim an over-budget body (in that order).

    Needs the policy because the per-slide-type body budget lives on it. Returns
    the payload unchanged when there is no body or no length/heading violation.
    """
    repaired = dict(payload)
    body = repaired.get("body")
    if not isinstance(body, str) or not body:
        return repaired
    codes = {violation.code for violation in violations}
    if VIOLATION_HEADING_REPEATED_IN_BODY in codes:
        heading = repaired.get("heading")
        if isinstance(heading, str) and heading.strip():
            body = _strip_heading_from_body(body, heading)
    if VIOLATION_BODY_TOO_LONG in codes:
        slide_type = str(repaired.get("slide_type") or repaired.get("type") or "")
        budget = body_budget_for_slide_type(slide_type, policy)
        if budget is not None:
            body = _trim_body_to_budget(body, budget.max_characters)
    repaired["body"] = body
    return repaired


__all__ = [
    "deterministic_repair_slide_payload",
    "repair_body_length_and_heading",
    "repair_text_sentence_case_en",
]
