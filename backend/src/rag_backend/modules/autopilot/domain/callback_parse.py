"""Parse Telegram callback_data. No I/O."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from rag_backend.modules.autopilot.constants import (
    GATE_CONTENT,
    GATE_DESIGN,
    GATE_IMAGES,
    GATE_OUTLINE,
)
from rag_backend.modules.autopilot.schedule_constants import (
    CALLBACK_SCHEDULE_PATTERN,
    CALLBACK_SLOT_PATTERN,
    KIND_SLOT,
)
from rag_backend.modules.autopilot.webhook_constants import (
    CALLBACK_ACTION_PATTERN,
    CALLBACK_PHASE_PATTERN,
    KIND_PHASE,
    PHASE_SLUG_DESIGN,
    PHASE_SLUG_IMAGES,
    PHASE_SLUG_OUTLINE,
    PHASE_SLUG_TEXT,
)

_ACTION = re.compile(CALLBACK_ACTION_PATTERN)
_PHASE = re.compile(CALLBACK_PHASE_PATTERN)
_SCHEDULE = re.compile(CALLBACK_SCHEDULE_PATTERN)
_SLOT = re.compile(CALLBACK_SLOT_PATTERN)

_PHASE_BY_TOKEN: dict[str, str] = {
    PHASE_SLUG_TEXT: GATE_CONTENT,
    PHASE_SLUG_DESIGN: GATE_DESIGN,
    PHASE_SLUG_IMAGES: GATE_IMAGES,
    PHASE_SLUG_OUTLINE: GATE_OUTLINE,
}


@dataclass(frozen=True, kw_only=True)
class ParsedCallback:
    """One allowlisted button. ``phase`` is set only for a rework-phase tap.

    ``epoch`` is set only for a slot tap: the slot's Unix seconds (AE-0370).
    """

    kind: str
    run_id: UUID
    phase: str = ""
    epoch: int = 0


def parse_callback(data: str) -> ParsedCallback | None:
    """``ap:<action>:<uuid>``, ``ap:rw:<phase>:<uuid>``, or ``ap:at:<epoch>:<uuid>``.

    Anything else is None. The Text button's token is ``text`` and maps to the
    content phase.
    """
    action = _ACTION.fullmatch(data) or _SCHEDULE.fullmatch(data)
    if action is not None:
        return ParsedCallback(kind=action.group(1), run_id=UUID(action.group(2)))
    slot = _SLOT.fullmatch(data)
    if slot is not None:
        return ParsedCallback(
            kind=KIND_SLOT, run_id=UUID(slot.group(2)), epoch=int(slot.group(1))
        )
    phase = _PHASE.fullmatch(data)
    if phase is None:
        return None
    mapped = _PHASE_BY_TOKEN.get(phase.group(1))
    if mapped is None:
        return None
    return ParsedCallback(kind=KIND_PHASE, run_id=UUID(phase.group(2)), phase=mapped)
