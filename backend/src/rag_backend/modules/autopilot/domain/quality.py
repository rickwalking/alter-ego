"""Content-quality violations: read from a gate, reported to a revise.

Pure. The snapshot reads the blocking violations of the gate's validation
report; the runner turns them into the ``Measured`` value (``rule@slide``
pairs) and one feedback line per failing slide with its offending text.
"""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.modules.autopilot.constants import (
    FIELD_CODE,
    FIELD_SEVERITY,
    FIELD_VIOLATIONS,
    SEVERITY_BLOCKER,
)
from rag_backend.modules.autopilot.domain.gate import QualityViolation
from rag_backend.modules.autopilot.quality_constants import (
    FIELD_FIELD,
    FIELD_LOCALE,
    FIELD_LOCALIZED_SLIDES,
    FIELD_MESSAGE,
    FIELD_SLIDE_INDEX,
    MAX_MEASURED_VIOLATIONS,
    MEASURED_PAIR,
    MEASURED_SEPARATOR,
    PAYLOAD_KEY_PREFIX,
    SLIDE_UNKNOWN,
    VIOLATION_LINE,
    VIOLATION_TEXT_MAX_CHARS,
    VIOLATION_TEXT_SUFFIX,
)


def quality_violations(
    report: object, state: Mapping[str, object]
) -> tuple[QualityViolation, ...]:
    """Blocking violations of ``report``, each with its slide's current text."""
    raw = report.get(FIELD_VIOLATIONS) if isinstance(report, Mapping) else None
    if not isinstance(raw, list):
        return ()
    slides = _slides_by_index(state.get(FIELD_LOCALIZED_SLIDES))
    found = (_violation(item, slides) for item in raw if isinstance(item, Mapping))
    return tuple(violation for violation in found if violation is not None)


def measured_pairs(violations: tuple[QualityViolation, ...]) -> str:
    """``rule@slide`` pairs, at most ``MAX_MEASURED_VIOLATIONS``, no repeats."""
    pairs = [
        MEASURED_PAIR.format(rule=item.rule, slide=_slide_label(item))
        for item in violations
    ]
    unique = list(dict.fromkeys(pairs))
    return MEASURED_SEPARATOR.join(unique[:MAX_MEASURED_VIOLATIONS])


def violation_lines(violations: tuple[QualityViolation, ...]) -> tuple[str, ...]:
    """One feedback line per violation (slide, rule, message, current text)."""
    lines = [_line(item) for item in violations]
    return tuple(dict.fromkeys(lines))[:MAX_MEASURED_VIOLATIONS]


def _line(item: QualityViolation) -> str:
    line = VIOLATION_LINE.format(
        slide=_slide_label(item),
        locale=item.locale,
        field=item.field,
        rule=item.rule,
        message=item.message,
    )
    if not item.text:
        return line
    return line + VIOLATION_TEXT_SUFFIX.format(
        text=item.text[:VIOLATION_TEXT_MAX_CHARS]
    )


def _slide_label(item: QualityViolation) -> str:
    if item.slide_index is None:
        return SLIDE_UNKNOWN
    return str(item.slide_index)


def _violation(
    item: Mapping[str, object], slides: Mapping[int, Mapping[str, object]]
) -> QualityViolation | None:
    severity = _text(item.get(FIELD_SEVERITY)) or SEVERITY_BLOCKER
    rule = _text(item.get(FIELD_CODE))
    if severity != SEVERITY_BLOCKER or not rule:
        return None
    index = item.get(FIELD_SLIDE_INDEX)
    slide_index = index if isinstance(index, int) else None
    locale = _text(item.get(FIELD_LOCALE))
    field = _text(item.get(FIELD_FIELD))
    return QualityViolation(
        rule=rule,
        slide_index=slide_index,
        locale=locale,
        field=field,
        message=_text(item.get(FIELD_MESSAGE)),
        text=_current_text(_slide(slides, slide_index), locale, field),
    )


def _slide(
    slides: Mapping[int, Mapping[str, object]], index: int | None
) -> Mapping[str, object] | None:
    if index is None:
        return None
    return slides.get(index)


def _current_text(slide: Mapping[str, object] | None, locale: str, field: str) -> str:
    """The plain-text field's copy, or empty (nested paths are not resolved)."""
    if slide is None or not locale or not field:
        return ""
    payload = slide.get(PAYLOAD_KEY_PREFIX + locale)
    if not isinstance(payload, Mapping):
        return ""
    return _text(payload.get(field)).strip()


def _slides_by_index(raw: object) -> dict[int, Mapping[str, object]]:
    if not isinstance(raw, list):
        return {}
    slides: dict[int, Mapping[str, object]] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        index = item.get(FIELD_SLIDE_INDEX)
        if isinstance(index, int):
            slides[index] = item
    return slides


def _text(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""
