"""Build a gate snapshot from a workflow-state mapping.

The mapping is the editorial checkpoint dict. Image bytes are measured
by the caller and passed in, so this module stays free of file I/O.
"""

from __future__ import annotations

from collections.abc import Mapping

from rag_backend.modules.autopilot.constants import (
    BLOCKER_BLOCKING,
    BLOCKER_MISSING,
    FIELD_BLOCKING,
    FIELD_CODE,
    FIELD_CONTENT,
    FIELD_CONTENT_GATE,
    FIELD_CURRENT_PHASE,
    FIELD_FORBIDDEN_HITS,
    FIELD_FORBIDDEN_PHRASES,
    FIELD_KEY_POINTS,
    FIELD_OUTLINE,
    FIELD_OVERALL,
    FIELD_PERSONA_SCORES,
    FIELD_PHASE_STATUS,
    FIELD_PRESENTATION_VALIDATION,
    FIELD_RESEARCH,
    FIELD_REVISION_COUNT,
    FIELD_SEVERITY,
    FIELD_SLIDE_DRAFTS,
    FIELD_SUMMARY,
    FIELD_VIOLATIONS,
    GATE_DESIGN,
    SEVERITY_BLOCKER,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateSnapshot,
    ResearchSourceFact,
    SnapshotParts,
)


def assemble_snapshot(parts: SnapshotParts) -> GateSnapshot:
    """Copy the fields the policy reads. Unknown shapes become empty."""
    state = parts.state
    phase = _text(state.get(FIELD_CURRENT_PHASE))
    blockers = _blockers(state.get(FIELD_PRESENTATION_VALIDATION), phase)
    return GateSnapshot(
        phase=phase,
        phase_status=_text(state.get(FIELD_PHASE_STATUS)),
        lock_version=parts.lock_version,
        sources=_sources(state.get(FIELD_RESEARCH)),
        outline_count=_list_len(state.get(FIELD_OUTLINE)),
        slides_total=parts.slides_total,
        persona_score=_persona_score(state.get(FIELD_PERSONA_SCORES)),
        forbidden_hits=_forbidden(state),
        presentation_blockers=blockers,
        images=parts.images,
        revisions_used=_revisions(state.get(FIELD_REVISION_COUNT), phase),
        stale=parts.stale,
        engine_blocker=parts.engine_blocker,
        parked=parts.parked,
        parked_overdue=parts.parked_overdue,
        hero_images_total=parts.hero_images_total,
    )


def _sources(raw: object) -> tuple[ResearchSourceFact, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(_source(item) for item in raw if isinstance(item, dict))


def _source(item: Mapping[str, object]) -> ResearchSourceFact:
    return ResearchSourceFact(
        content=_text(item.get(FIELD_CONTENT)),
        summary=_text(item.get(FIELD_SUMMARY)),
        key_points=_strings(item.get(FIELD_KEY_POINTS)),
    )


def _persona_score(raw: object) -> float | None:
    """The lowest persona score, or None when the run was not scored (AE-0364).

    None means "not scored" (no persona), which the policy skips like the
    engine does. An entry that is present but unreadable counts as 0, so the
    gate fails closed instead of approving into an engine error.
    """
    if not isinstance(raw, dict) or not raw:
        return None
    return min(_one_score(value) for value in raw.values())


def _one_score(value: object) -> float:
    if isinstance(value, dict):
        # The engine reads a missing ``overall`` as 0 (QA r1 B1); so do we.
        return _float_or_zero(value.get(FIELD_OVERALL, 0))
    return _float_or_zero(value)


def _float_or_zero(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0
    return float(value)


def _forbidden(state: Mapping[str, object]) -> tuple[str, ...]:
    hits = list(_strings(state.get(FIELD_FORBIDDEN_HITS)))
    hits.extend(_violation_codes(state.get(FIELD_CONTENT_GATE)))
    hits.extend(_phrase_scan(state))
    return tuple(dict.fromkeys(hits))


def _phrase_scan(state: Mapping[str, object]) -> tuple[str, ...]:
    phrases = _strings(state.get(FIELD_FORBIDDEN_PHRASES))
    if not phrases:
        return ()
    blob = _draft_text(state.get(FIELD_SLIDE_DRAFTS)).casefold()
    return tuple(phrase for phrase in phrases if phrase.casefold() in blob)


def _draft_text(raw: object) -> str:
    if not isinstance(raw, list):
        return ""
    parts: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            parts.extend(_text(value) for value in item.values())
        elif isinstance(item, str):
            parts.append(item)
    return " ".join(parts)


def _blockers(raw: object, phase: str) -> tuple[str, ...]:
    if phase != GATE_DESIGN:
        return ()
    if not isinstance(raw, dict):
        return (BLOCKER_MISSING,)
    if raw.get(FIELD_BLOCKING) is True:
        return (BLOCKER_BLOCKING,)
    return _violation_codes(raw)


def _violation_codes(raw: object) -> tuple[str, ...]:
    payload = raw.get(FIELD_VIOLATIONS) if isinstance(raw, dict) else raw
    if not isinstance(payload, list):
        return ()
    codes: list[str] = []
    for item in payload:
        code = _blocker_code(item)
        if code:
            codes.append(code)
    return tuple(codes)


def _blocker_code(item: object) -> str:
    if not isinstance(item, dict):
        return ""
    severity = _text(item.get(FIELD_SEVERITY)) or SEVERITY_BLOCKER
    if severity != SEVERITY_BLOCKER:
        return ""
    if FIELD_CODE in item:
        return _text(item.get(FIELD_CODE))
    return SEVERITY_BLOCKER


def _revisions(raw: object, phase: str) -> int:
    if not isinstance(raw, dict):
        return 0
    value = raw.get(phase, 0)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _list_len(raw: object) -> int:
    if isinstance(raw, list):
        return len(raw)
    return 0


def _strings(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(_text(item) for item in raw if _text(item))


def _text(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""
