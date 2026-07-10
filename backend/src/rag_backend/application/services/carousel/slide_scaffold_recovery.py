"""Deterministic recovery of slide locale payloads from drafting scaffolds.

AE-0309: when the localized slide builder reports a typed parse failure (the
draft output was a raw ``## PT / **Heading:** / **Body:**`` scaffold or the
built payload misses canonical keys), this module attempts a bounded
deterministic repair — scaffold section extraction, label stripping, and
canonical shape normalization — before the single LLM retry runs.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from rag_backend.application.services.carousel.slide_parse_failures import (
    CANONICAL_KEY_CONTENT_KIND,
    CANONICAL_KEY_FEATURES,
    PARSE_FAILURE_RAW_DRAFT_FALLBACK,
    SlideParseFailure,
    attach_parse_failure_marker,
    is_clean_draft_copy,
)
from rag_backend.domain.constants.carousel import (
    LANGUAGE_EN,
    LANGUAGE_PT,
    SLIDE_TYPE_CONTENT,
)
from rag_backend.domain.constants.carousel_presentation import (
    CONTENT_KIND_FEATURES,
    CONTENT_KIND_INSIGHT,
    CONTENT_KIND_STATS,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_PRESENTATION_EN,
    STATE_FIELD_PRESENTATION_PT,
    STATE_FIELD_SLIDE_INDEX,
    STATE_FIELD_SLIDE_TYPE,
)

_KEY_HEADING = "heading"
_KEY_BODY = "body"
_KEY_STATS = "stats"
_KEY_INSIGHT = "insight"

_LOCALE_PAYLOAD_KEYS: dict[str, str] = {
    LANGUAGE_PT: STATE_FIELD_PRESENTATION_PT,
    LANGUAGE_EN: STATE_FIELD_PRESENTATION_EN,
}
_LOCALE_SECTION_TITLES: dict[str, str] = {
    LANGUAGE_PT: "PT",
    LANGUAGE_EN: "EN",
}

_SECTION_PATTERN = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)
_SECTION_LINE = re.compile(r"^\s*##\s+.*$")
_LABEL_LINE = re.compile(r"^\*\*(?P<label>[A-Za-z ]+):\*\*\s*(?P<value>.*)$")
_INLINE_LABEL_PREFIX = re.compile(r"^\s*\*\*[A-Za-z ]+:\*\*\s*")
_PLAIN_LABEL_PREFIX = re.compile(
    r"^\s*(?:SLIDE\s*\d+|TITLE|BODY|KEY\s*POINTS)\s*:\s*",
    re.IGNORECASE,
)


def split_scaffold_sections(raw: str) -> dict[str, str]:
    """Split ``## <title>`` markdown sections into an upper-title → body map."""
    sections: dict[str, str] = {}
    matches = list(_SECTION_PATTERN.finditer(raw))
    for position, match in enumerate(matches):
        start = match.end()
        end = matches[position + 1].start() if position + 1 < len(matches) else len(raw)
        sections[match.group("title").strip().upper()] = raw[start:end].strip()
    return sections


def _labeled_values(section: str) -> dict[str, str]:
    """Parse ``**Label:** value`` lines (with continuation lines) in a section."""
    values: dict[str, str] = {}
    current: str | None = None
    for line in section.splitlines():
        match = _LABEL_LINE.match(line.strip())
        if match is not None:
            current = match.group("label").strip().lower()
            values[current] = match.group("value").strip()
        elif current is not None and line.strip():
            values[current] = f"{values[current]}\n{line.strip()}".strip()
    return values


def extract_scaffold_locale_copy(raw: str, locale: str) -> dict[str, str] | None:
    """Extract heading/body copy for one locale from a ``## PT / ## EN`` scaffold."""
    section_title = _LOCALE_SECTION_TITLES.get(locale, "")
    section = split_scaffold_sections(raw).get(section_title, "")
    if not section:
        return None
    values = _labeled_values(section)
    heading = values.get(_KEY_HEADING, "")
    body = values.get(_KEY_BODY, "")
    if not heading and not body:
        return None
    return {_KEY_HEADING: heading, _KEY_BODY: body}


def strip_scaffold_labels(text: str) -> str:
    """Drop section-header lines and strip scaffold label prefixes from copy."""
    cleaned: list[str] = []
    for line in text.splitlines():
        if _SECTION_LINE.match(line):
            continue
        stripped = _INLINE_LABEL_PREFIX.sub("", line)
        stripped = _PLAIN_LABEL_PREFIX.sub("", stripped)
        if stripped.strip():
            cleaned.append(stripped.strip())
    return "\n".join(cleaned)


def recover_scaffold_body(text: str, locale: str) -> str:
    """Recover visible body copy from scaffold-contaminated text.

    Prefers extracting the locale's ``## PT`` / ``## EN`` section; otherwise
    strips scaffold label prefixes. Returns the original text when nothing
    usable survives so the violation stays visible instead of hiding copy.
    """
    extracted = extract_scaffold_locale_copy(text, locale)
    if extracted is not None and extracted[_KEY_BODY]:
        return extracted[_KEY_BODY]
    stripped = strip_scaffold_labels(text)
    return stripped or text


def _infer_content_kind(payload: Mapping[str, object]) -> str:
    if payload.get(_KEY_STATS) is not None:
        return CONTENT_KIND_STATS
    if payload.get(_KEY_INSIGHT) is not None:
        return CONTENT_KIND_INSIGHT
    return CONTENT_KIND_FEATURES


def normalize_canonical_shape(payload: dict[str, object]) -> dict[str, object]:
    """Fill canonical content keys so payloads always carry the full shape."""
    if str(payload.get(STATE_FIELD_SLIDE_TYPE) or "") != SLIDE_TYPE_CONTENT:
        return payload
    normalized = dict(payload)
    if CANONICAL_KEY_CONTENT_KIND not in normalized:
        normalized[CANONICAL_KEY_CONTENT_KIND] = _infer_content_kind(normalized)
    features_kind = normalized.get(CANONICAL_KEY_CONTENT_KIND) == CONTENT_KIND_FEATURES
    if features_kind and CANONICAL_KEY_FEATURES not in normalized:
        normalized[CANONICAL_KEY_FEATURES] = []
    return normalized


def _recover_body_copy(failure: SlideParseFailure) -> dict[str, str] | None:
    """Deterministically derive heading/body copy from the withheld raw draft."""
    raw = failure.raw_draft
    if not raw.strip():
        return None
    extracted = extract_scaffold_locale_copy(raw, failure.locale)
    if extracted is not None:
        return extracted if extracted[_KEY_BODY] else None
    stripped = strip_scaffold_labels(raw)
    if stripped and is_clean_draft_copy(stripped):
        return {_KEY_HEADING: "", _KEY_BODY: stripped}
    return None


def _recover_one(slide: dict[str, object], failure: SlideParseFailure) -> bool:
    """Apply one deterministic recovery; return True when it succeeded."""
    locale_key = _LOCALE_PAYLOAD_KEYS.get(failure.locale)
    if locale_key is None:
        return False
    raw_payload = slide.get(locale_key)
    payload = dict(raw_payload) if isinstance(raw_payload, dict) else {}
    if failure.reason == PARSE_FAILURE_RAW_DRAFT_FALLBACK:
        copy = _recover_body_copy(failure)
        if copy is None:
            return False
        if copy[_KEY_HEADING] and not str(payload.get(_KEY_HEADING) or "").strip():
            payload[_KEY_HEADING] = copy[_KEY_HEADING]
        payload[_KEY_BODY] = copy[_KEY_BODY]
    slide[locale_key] = normalize_canonical_shape(payload)
    return True


def recover_parse_failures(
    slides: list[dict[str, object]],
    failures: list[SlideParseFailure],
) -> tuple[list[dict[str, object]], list[SlideParseFailure]]:
    """Recover failed locale payloads deterministically; mark what remains."""
    if not failures:
        return slides, []
    recovered_slides = [dict(slide) for slide in slides]
    by_index: dict[int, dict[str, object]] = {}
    for slide in recovered_slides:
        index = slide.get(STATE_FIELD_SLIDE_INDEX)
        if isinstance(index, int):
            by_index[index] = slide
    remaining: list[SlideParseFailure] = []
    for failure in failures:
        slide = by_index.get(failure.slide_index)
        if slide is None or not _recover_one(slide, failure):
            remaining.append(failure)
            if slide is not None:
                attach_parse_failure_marker(slide, failure)
    return recovered_slides, remaining


__all__ = [
    "extract_scaffold_locale_copy",
    "normalize_canonical_shape",
    "recover_parse_failures",
    "recover_scaffold_body",
    "split_scaffold_sections",
    "strip_scaffold_labels",
]
