"""Constants for the content-gate targeted field repair.

When the content gate blocks, the failing fields (and only those) go to the
model with their slide/locale/field path, current text, exact limit and the
rule they break; the answers are patched in by path and re-validated, at most
``GATE_REPAIR_MAX_ROUNDS`` times.

Each repair round after the gate blocks is one model call, and one round sends a bounded
number of fields (the rest wait for the next round). The model answers ``{"fixes":
[{"id": "...", "text": "..."}]}`` with target ids ``<slide>:<locale>:<field path>``. A
field filled from PT for a shape mismatch gets the missing-EN problem.
"""

from __future__ import annotations

from typing import Final

GATE_REPAIR_MAX_ROUNDS: Final[int] = 2
GATE_REPAIR_MAX_TARGETS: Final[int] = 40
GATE_REPAIR_TIMEOUT_SECONDS: Final[float] = 180.0

GATE_REPAIR_PROMPT_DOMAIN: Final[str] = "carousel_gate_repair"
GATE_REPAIR_PROMPT_NAME: Final[str] = "field_repair"
GATE_REPAIR_PROMPT_VERSION: Final[str] = "v1"

GATE_REPAIR_VAR_FIELDS_JSON: Final[str] = "fields_json"
GATE_REPAIR_VAR_STYLE_GUIDE: Final[str] = "style_guide"

GATE_REPAIR_JSON_FIXES_KEY: Final[str] = "fixes"
GATE_REPAIR_JSON_ID_KEY: Final[str] = "id"
GATE_REPAIR_JSON_TEXT_KEY: Final[str] = "text"

GATE_REPAIR_FIELD_SLIDE: Final[str] = "slide"
GATE_REPAIR_FIELD_LOCALE: Final[str] = "locale"
GATE_REPAIR_FIELD_PATH: Final[str] = "field"
GATE_REPAIR_FIELD_TEXT: Final[str] = "current_text"
GATE_REPAIR_FIELD_PT_TEXT: Final[str] = "portuguese_source"
GATE_REPAIR_FIELD_MAX_CHARS: Final[str] = "max_characters"
GATE_REPAIR_FIELD_MAX_LINES: Final[str] = "max_lines"
GATE_REPAIR_FIELD_PROBLEMS: Final[str] = "problems"
GATE_REPAIR_FIELD_SLIDE_HEADING: Final[str] = "slide_heading"

GATE_REPAIR_TARGET_ID: Final[str] = "{slide}:{locale}:{field}"
GATE_REPAIR_PROBLEM_MISSING_EN: Final[str] = (
    "translation_shape_mismatch: missing in English; translate the Portuguese source"
)
GATE_REPAIR_PROBLEM_LINE: Final[str] = "{code}: {message}"

GATE_REVISION_NOTE_HEADER: Final[str] = (
    "Content gate violations to fix (keep every limit):"
)
GATE_REVISION_NOTE_LINE: Final[str] = "- Slide {slide} {locale} {field}: {message}"
GATE_REVISION_NOTE_SLIDE_FIELD: Final[str] = "slide"
GATE_REVISION_NOTE_NO_LOCALE: Final[str] = "PT+EN"

LOG_GATE_REPAIR_ROUND: Final[str] = "content_gate_repair_round"
LOG_GATE_REPAIR_DONE: Final[str] = "content_gate_repair_done"
LOG_GATE_REPAIR_MODEL_FAILED: Final[str] = "content_gate_repair_model_failed"

__all__ = [
    "GATE_REPAIR_FIELD_LOCALE",
    "GATE_REPAIR_FIELD_MAX_CHARS",
    "GATE_REPAIR_FIELD_MAX_LINES",
    "GATE_REPAIR_FIELD_PATH",
    "GATE_REPAIR_FIELD_PROBLEMS",
    "GATE_REPAIR_FIELD_PT_TEXT",
    "GATE_REPAIR_FIELD_SLIDE",
    "GATE_REPAIR_FIELD_SLIDE_HEADING",
    "GATE_REPAIR_FIELD_TEXT",
    "GATE_REPAIR_JSON_FIXES_KEY",
    "GATE_REPAIR_JSON_ID_KEY",
    "GATE_REPAIR_JSON_TEXT_KEY",
    "GATE_REPAIR_MAX_ROUNDS",
    "GATE_REPAIR_MAX_TARGETS",
    "GATE_REPAIR_PROBLEM_LINE",
    "GATE_REPAIR_PROBLEM_MISSING_EN",
    "GATE_REPAIR_PROMPT_DOMAIN",
    "GATE_REPAIR_PROMPT_NAME",
    "GATE_REPAIR_PROMPT_VERSION",
    "GATE_REPAIR_TARGET_ID",
    "GATE_REPAIR_TIMEOUT_SECONDS",
    "GATE_REPAIR_VAR_FIELDS_JSON",
    "GATE_REPAIR_VAR_STYLE_GUIDE",
    "GATE_REVISION_NOTE_HEADER",
    "GATE_REVISION_NOTE_LINE",
    "GATE_REVISION_NOTE_NO_LOCALE",
    "GATE_REVISION_NOTE_SLIDE_FIELD",
    "LOG_GATE_REPAIR_DONE",
    "LOG_GATE_REPAIR_MODEL_FAILED",
    "LOG_GATE_REPAIR_ROUND",
]
