"""Typed per-locale slide parse failures for the fail-closed content gate.

AE-0309: a drafting parse failure must never silently store the raw drafting
scaffold as visible slide copy. The localized slide builder reports typed
:class:`SlideParseFailure` values instead of falling back to the raw draft;
unrecovered failures are persisted as slide-level markers so every validation
path (write, read resolvers, approval blocking checks) derives a blocking
``slide_parse_failed`` violation from them.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.presentation_validation_fields import (
    contains_drafting_scaffold,
)
from rag_backend.domain.constants.carousel import SLIDE_TYPE_CONTENT
from rag_backend.domain.constants.carousel_presentation import (
    CONTENT_KIND_FEATURES,
    VIOLATION_SLIDE_PARSE_FAILED,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_SLIDE_INDEX,
    STATE_FIELD_SLIDE_TYPE,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation

PARSE_FAILURE_RAW_DRAFT_FALLBACK = "raw_draft_fallback"
PARSE_FAILURE_MISSING_CANONICAL_KEYS = "missing_canonical_keys"

# Slide-level marker key for unrecovered parse failures. Stored alongside the
# localized payloads so read-path validation stays fail-closed after a restart.
SLIDE_PARSE_FAILURES_KEY = "parse_failures"
PARSE_FAILURE_FIELD_LOCALE = "locale"
PARSE_FAILURE_FIELD_REASON = "reason"

PARSE_FAILURE_MESSAGE = (
    "Slide copy could not be parsed from the draft output; "
    "the raw draft was withheld from the visible body"
)

# Canonical locale payload shape (AE-0309): every payload carries these keys;
# content slides must additionally carry content_kind (+ features for the
# features kind). A partial dict is itself a parse failure.
CANONICAL_LOCALE_KEYS: tuple[str, ...] = ("slide_type", "heading", "body")
CANONICAL_KEY_CONTENT_KIND = "content_kind"
CANONICAL_KEY_FEATURES = "features"

_FIELD_BODY = "body"
_JSON_BLOB_PREFIX = "{"
_MARKDOWN_SECTION_MARKER = "## "
_BOLD_LABEL_PATTERN = re.compile(r"\*\*[A-Za-z ]+:\*\*")


@dataclass(frozen=True)
class SlideParseFailure:
    """One locale payload that could not be parsed from a slide draft."""

    slide_index: int
    locale: str
    reason: str
    raw_draft: str = ""


def is_clean_draft_copy(text: str) -> bool:
    """Return True when raw draft text is plain copy safe to use as body."""
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.startswith(_JSON_BLOB_PREFIX):
        return False
    if _MARKDOWN_SECTION_MARKER in stripped:
        return False
    if _BOLD_LABEL_PATTERN.search(stripped) is not None:
        return False
    return not contains_drafting_scaffold(stripped)


def missing_canonical_keys(payload: Mapping[str, object]) -> tuple[str, ...]:
    """Return canonical keys absent from a built locale payload."""
    required = list(CANONICAL_LOCALE_KEYS)
    if str(payload.get(STATE_FIELD_SLIDE_TYPE) or "") == SLIDE_TYPE_CONTENT:
        required.append(CANONICAL_KEY_CONTENT_KIND)
        kind = payload.get(CANONICAL_KEY_CONTENT_KIND)
        if kind is None or kind == CONTENT_KIND_FEATURES:
            required.append(CANONICAL_KEY_FEATURES)
    return tuple(key for key in required if key not in payload)


def parse_failure_violation(failure: SlideParseFailure) -> SlideValidationViolation:
    """Build the blocking validation violation for one parse failure."""
    return SlideValidationViolation(
        code=VIOLATION_SLIDE_PARSE_FAILED,
        message=PARSE_FAILURE_MESSAGE,
        slide_index=failure.slide_index,
        locale=failure.locale,
        field=_FIELD_BODY,
    )


def parse_failure_marker(failure: SlideParseFailure) -> dict[str, object]:
    """Serialize one parse failure into a state-storable marker dict."""
    return {
        PARSE_FAILURE_FIELD_LOCALE: failure.locale,
        PARSE_FAILURE_FIELD_REASON: failure.reason,
    }


def attach_parse_failure_marker(
    slide: dict[str, object],
    failure: SlideParseFailure,
) -> None:
    """Attach an unrecovered parse-failure marker to a localized slide record."""
    raw = slide.get(SLIDE_PARSE_FAILURES_KEY)
    markers = (
        [item for item in raw if isinstance(item, dict)]
        if isinstance(raw, list)
        else []
    )
    markers.append(parse_failure_marker(failure))
    slide[SLIDE_PARSE_FAILURES_KEY] = markers


def drop_parse_failure_marker(slide: dict[str, object], locale: str) -> None:
    """Remove a locale's parse-failure marker (e.g. after a reviewer edit)."""
    raw = slide.get(SLIDE_PARSE_FAILURES_KEY)
    if not isinstance(raw, list):
        return
    kept = [
        item
        for item in raw
        if isinstance(item, dict) and item.get(PARSE_FAILURE_FIELD_LOCALE) != locale
    ]
    if kept:
        slide[SLIDE_PARSE_FAILURES_KEY] = kept
    else:
        slide.pop(SLIDE_PARSE_FAILURES_KEY, None)


def marker_violations(
    slide: Mapping[str, object],
) -> list[SlideValidationViolation]:
    """Derive blocking violations from stored parse-failure markers."""
    raw = slide.get(SLIDE_PARSE_FAILURES_KEY)
    if not isinstance(raw, list):
        return []
    slide_index_value = slide.get(STATE_FIELD_SLIDE_INDEX)
    slide_index = slide_index_value if isinstance(slide_index_value, int) else None
    violations: list[SlideValidationViolation] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        locale_value = item.get(PARSE_FAILURE_FIELD_LOCALE)
        violations.append(
            SlideValidationViolation(
                code=VIOLATION_SLIDE_PARSE_FAILED,
                message=PARSE_FAILURE_MESSAGE,
                slide_index=slide_index,
                locale=str(locale_value) if locale_value else None,
                field=_FIELD_BODY,
            )
        )
    return violations


__all__ = [
    "CANONICAL_KEY_CONTENT_KIND",
    "CANONICAL_KEY_FEATURES",
    "CANONICAL_LOCALE_KEYS",
    "PARSE_FAILURE_FIELD_LOCALE",
    "PARSE_FAILURE_FIELD_REASON",
    "PARSE_FAILURE_MESSAGE",
    "PARSE_FAILURE_MISSING_CANONICAL_KEYS",
    "PARSE_FAILURE_RAW_DRAFT_FALLBACK",
    "SLIDE_PARSE_FAILURES_KEY",
    "SlideParseFailure",
    "attach_parse_failure_marker",
    "drop_parse_failure_marker",
    "is_clean_draft_copy",
    "marker_violations",
    "missing_canonical_keys",
    "parse_failure_marker",
    "parse_failure_violation",
]
