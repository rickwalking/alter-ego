"""Bounded rule ids for a content-gate event.

The value comes only from the known violation constants, so a message, slide text
or field value cannot reach a stored event even through the ``code`` field. One
detail string must pass the sanitizer's safe-code pattern (64 characters, no comma
or space), so "." joins the codes. Blockers are kept ahead of warnings, and a warning
is stored only when no blocker was dropped.
"""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.domain.constants.carousel_presentation import SEVERITY_WARNING
from rag_backend.domain.constants.violation_codes import KNOWN_VIOLATION_CODES
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_BLOCKING,
    STATE_FIELD_VIOLATION_CODE,
    STATE_FIELD_VIOLATION_SEVERITY,
    STATE_FIELD_VIOLATIONS,
)
from rag_backend.modules.generation_queue.constants import (
    DETAIL_TRUNCATED,
    DETAIL_VIOLATION_CODES,
    VIOLATION_CODES_MAX_CHARS,
    VIOLATION_CODES_SEPARATOR,
)


def violation_code_details(validation: Mapping[object, object]) -> dict[str, object]:
    """Return the fired rule ids, or nothing when no rule fired.

    The key is left out when empty because the sanitizer treats an empty string as
    an omission. Any code that is not stored marks the details ``truncated``.
    """
    rules = [(_known_code(entry), _blocks(entry)) for entry in _entries(validation)]
    blockers = {code for code, blocks in rules if code and blocks}
    warnings = {code for code, _ in rules if code} - blockers
    lost_blocker = any(blocks for code, blocks in rules if code is None)
    kept = _stored(sorted(blockers), [] if lost_blocker else sorted(warnings))
    details: dict[str, object] = {}
    if kept:
        details[DETAIL_VIOLATION_CODES] = VIOLATION_CODES_SEPARATOR.join(sorted(kept))
    if any(code is None for code, _ in rules) or len(kept) < len(blockers | warnings):
        details[DETAIL_TRUNCATED] = True
    return details


def _entries(validation: Mapping[object, object]) -> list[object]:
    entries: list[object] = []
    for key in (STATE_FIELD_VIOLATIONS, STATE_FIELD_BLOCKING):
        value = validation.get(key)
        if isinstance(value, list):
            entries.extend(value)
    return entries


def _known_code(entry: object) -> str | None:
    if not isinstance(entry, Mapping):
        return None
    code = entry.get(STATE_FIELD_VIOLATION_CODE)
    return code if isinstance(code, str) and code in KNOWN_VIOLATION_CODES else None


def _blocks(entry: object) -> bool:
    """Return whether an entry blocks, as the violation model defaults."""
    if not isinstance(entry, Mapping):
        return True
    return entry.get(STATE_FIELD_VIOLATION_SEVERITY) != SEVERITY_WARNING


def _stored(blockers: list[str], warnings: list[str]) -> list[str]:
    """Add warnings only when every blocker fits, so none reads as a lost blocker."""
    kept = _fit(blockers)
    if len(kept) < len(blockers):
        return kept
    return _fit([*kept, *warnings])


def _fit(ranked: list[str]) -> list[str]:
    """Keep codes in rank order while the joined string stays within its budget."""
    kept: list[str] = []
    used = 0
    for code in ranked:
        cost = len(code) + (len(VIOLATION_CODES_SEPARATOR) if kept else 0)
        if used + cost > VIOLATION_CODES_MAX_CHARS:
            continue
        kept.append(code)
        used += cost
    return kept


__all__ = ["violation_code_details"]
