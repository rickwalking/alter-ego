"""Bounded rule ids for a content-gate event.

The value comes only from the known violation constants, so a message, slide text
or field value cannot reach a stored event even through the ``code`` field. One
detail string must pass the sanitizer's safe-code pattern (64 characters, no comma
or space), so "." joins the codes and blockers are kept ahead of warnings.
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
    rules = [_rule(entry) for entry in _entries(validation)]
    fired = [rule for rule in rules if rule is not None]
    blockers = {code for code, blocks in fired if blocks}
    warnings = {code for code, _ in fired} - blockers
    kept = _fit([*sorted(blockers), *sorted(warnings)])
    details: dict[str, object] = {}
    if kept:
        details[DETAIL_VIOLATION_CODES] = VIOLATION_CODES_SEPARATOR.join(sorted(kept))
    if len(fired) < len(rules) or len(kept) < len(blockers | warnings):
        details[DETAIL_TRUNCATED] = True
    return details


def _entries(validation: Mapping[object, object]) -> list[object]:
    entries: list[object] = []
    for key in (STATE_FIELD_VIOLATIONS, STATE_FIELD_BLOCKING):
        value = validation.get(key)
        if isinstance(value, list):
            entries.extend(value)
    return entries


def _rule(entry: object) -> tuple[str, bool] | None:
    """Return a known code and whether it blocks, as the violation model defaults."""
    if not isinstance(entry, Mapping):
        return None
    code = entry.get(STATE_FIELD_VIOLATION_CODE)
    if not isinstance(code, str) or code not in KNOWN_VIOLATION_CODES:
        return None
    return code, entry.get(STATE_FIELD_VIOLATION_SEVERITY) != SEVERITY_WARNING


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
