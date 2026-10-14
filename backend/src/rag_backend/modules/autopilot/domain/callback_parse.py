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

_PHASE_BY_TOKEN: dict[str, str] = {
    PHASE_SLUG_TEXT: GATE_CONTENT,
    PHASE_SLUG_DESIGN: GATE_DESIGN,
    PHASE_SLUG_IMAGES: GATE_IMAGES,
    PHASE_SLUG_OUTLINE: GATE_OUTLINE,
}


@dataclass(frozen=True, kw_only=True)
class ParsedCallback:
    """One allowlisted button. ``phase`` is set only for a rework-phase tap."""

    kind: str
    run_id: UUID
    phase: str = ""


def parse_callback(data: str) -> ParsedCallback | None:
    """``ap:<action>:<uuid>`` or ``ap:rw:<phase>:<uuid>``. Anything else is None.

    The Text button's token is ``text`` and maps to the content phase.
    """
    action = _ACTION.fullmatch(data)
    if action is not None:
        return ParsedCallback(kind=action.group(1), run_id=UUID(action.group(2)))
    phase = _PHASE.fullmatch(data)
    if phase is None:
        return None
    mapped = _PHASE_BY_TOKEN.get(phase.group(1))
    if mapped is None:
        return None
    return ParsedCallback(kind=KIND_PHASE, run_id=UUID(phase.group(2)), phase=mapped)
