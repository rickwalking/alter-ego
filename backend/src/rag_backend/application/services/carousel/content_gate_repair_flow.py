"""Where the content ensure uses the targeted gate repair (AE-0430).

- ``repair_blocked_content_gate``: after the content review build (drafting,
  translation and any revision all happen before it), a blocking
  ``content_gate_validation`` runs the field repair loop. The repaired slides
  are written back exactly like owner edits (``apply_localized_slide_edits``),
  so the drafts, the EN translations and both reports stay in step.
- ``gate_violation_note``: a revision request carries the current blocking
  violations next to the owner's note, so "fix the validation errors" is
  actionable for the drafting model.
- ``visible_copy_changed``: a revision note is ``applied`` only when the
  visible slide copy changed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from rag_backend.application.services.carousel.content_gate_repair import (
    GateFieldRepairer,
    GateRepairCommand,
    run_gate_repair,
)
from rag_backend.application.services.carousel.localized_slide_builder import (
    PRESENTATION_EN_KEY,
    PRESENTATION_PT_KEY,
)
from rag_backend.application.services.carousel.presentation_review_edits import (
    apply_localized_slide_edits,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY,
)
from rag_backend.domain.constants.carousel_presentation import SEVERITY_BLOCKER
from rag_backend.domain.constants.content_gate_repair import (
    GATE_REVISION_NOTE_HEADER,
    GATE_REVISION_NOTE_LINE,
    GATE_REVISION_NOTE_NO_LOCALE,
    GATE_REVISION_NOTE_SLIDE_FIELD,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_BLOCKING,
    STATE_FIELD_CONTENT_GATE_VALIDATION,
    STATE_FIELD_SLIDE_INDEX,
    STATE_FIELD_VIOLATIONS,
)

_SEVERITY_KEY = "severity"
_CODE_KEY = "code"
_MESSAGE_KEY = "message"
_LOCALE_KEY = "locale"
_FIELD_KEY = "field"


@dataclass(frozen=True)
class GateRepairContext:
    """The repairer (None: repair off), the author's style guide, the project."""

    repairer: GateFieldRepairer | None
    style_guide: str = ""
    project_id: str = ""


def _blocking_gate(source: Mapping[str, object]) -> Mapping[str, object] | None:
    gate = source.get(STATE_FIELD_CONTENT_GATE_VALIDATION)
    if not isinstance(gate, Mapping) or gate.get(STATE_FIELD_BLOCKING) is not True:
        return None
    return gate


def _slides(source: Mapping[str, object]) -> list[dict[str, object]]:
    raw = source.get(WORKFLOW_STATE_LOCALIZED_SLIDES_KEY)
    if not isinstance(raw, list):
        return []
    return [slide for slide in raw if isinstance(slide, dict)]


def _policy_version(source: Mapping[str, object]) -> str | None:
    value = source.get(WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY)
    return value if isinstance(value, str) and value.strip() else None


async def repair_blocked_content_gate(
    state: Mapping[str, object],
    updates: Mapping[str, object],
    context: GateRepairContext,
) -> dict[str, object]:
    """Updates after repairing a blocked content gate; {} when nothing changed."""
    merged: dict[str, object] = {**state, **updates}
    slides = _slides(merged)
    if context.repairer is None or _blocking_gate(merged) is None or not slides:
        return {}
    outcome = await run_gate_repair(
        GateRepairCommand(
            slides=slides,
            repairer=context.repairer,
            policy_version=_policy_version(merged),
            style_guide=context.style_guide,
            project_id=context.project_id,
        )
    )
    if not outcome.changed_indices:
        return {}
    edited = [
        slide
        for slide in outcome.slides
        if slide.get(STATE_FIELD_SLIDE_INDEX) in outcome.changed_indices
    ]
    return apply_localized_slide_edits(merged, edited)


def _note_line(violation: Mapping[str, object]) -> str:
    return GATE_REVISION_NOTE_LINE.format(
        slide=violation.get(STATE_FIELD_SLIDE_INDEX),
        locale=str(violation.get(_LOCALE_KEY) or GATE_REVISION_NOTE_NO_LOCALE).upper(),
        field=violation.get(_FIELD_KEY) or GATE_REVISION_NOTE_SLIDE_FIELD,
        message=f"{violation.get(_CODE_KEY)}: {violation.get(_MESSAGE_KEY)}",
    )


def gate_violation_note(state: Mapping[str, object]) -> str | None:
    """The blocking violations as a revision note line block (None: none)."""
    gate = _blocking_gate(state)
    raw = gate.get(STATE_FIELD_VIOLATIONS) if gate is not None else None
    if not isinstance(raw, list):
        return None
    lines = [
        _note_line(violation)
        for violation in raw
        if isinstance(violation, Mapping)
        and violation.get(_SEVERITY_KEY, SEVERITY_BLOCKER) == SEVERITY_BLOCKER
    ]
    if not lines:
        return None
    return "\n".join([GATE_REVISION_NOTE_HEADER, *lines])


def _copy_signature(source: Mapping[str, object]) -> str:
    return json.dumps(
        [
            [slide.get(PRESENTATION_PT_KEY), slide.get(PRESENTATION_EN_KEY)]
            for slide in _slides(source)
        ],
        sort_keys=True,
        ensure_ascii=False,
    )


def visible_copy_changed(
    state: Mapping[str, object], updates: Mapping[str, object]
) -> bool:
    """True when the updated localized slides differ from the stored ones."""
    if WORKFLOW_STATE_LOCALIZED_SLIDES_KEY not in updates:
        return False
    return _copy_signature(state) != _copy_signature(updates)


__all__ = [
    "GateRepairContext",
    "gate_violation_note",
    "repair_blocked_content_gate",
    "visible_copy_changed",
]
