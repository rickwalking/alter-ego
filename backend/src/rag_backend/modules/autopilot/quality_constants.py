"""Constants for the content-quality gate reason and its repair (AE-0392).

A blocking presentation rule (sentence case, empty body, EN equal to PT, item
counts, tag balance...) is a ``content_quality`` failure, not a forbidden
phrase. The runner repairs it deterministically before it revises, and the
revise feedback names each failing slide.
"""

from __future__ import annotations

from rag_backend.modules.autopilot.constants import GATE_CONTENT, GATE_DESIGN

REASON_CONTENT_QUALITY = "content_quality"

# "Measured" lists at most this many ``rule@slide`` pairs; so does the
# per-slide violation list in the feedback.
MAX_MEASURED_VIOLATIONS = 10
MEASURED_PAIR = "{rule}@{slide}"
MEASURED_SEPARATOR = ", "
MEASURED_RATIO = "{got}/{expected}"
# The slide of a carousel-wide rule (slide count, for example).
SLIDE_UNKNOWN = "carousel"
VIOLATION_LINE = "slide {slide} ({locale} {field}): {rule}. {message}"
VIOLATION_TEXT_SUFFIX = ' Current text: "{text}".'
VIOLATION_TEXT_MAX_CHARS = 200

# Gates the same presentation validator blocks: repaired before a revise.
QUALITY_GATES: frozenset[str] = frozenset({GATE_CONTENT, GATE_DESIGN})

FIELD_MESSAGE = "message"
FIELD_SLIDE_INDEX = "slide_index"
FIELD_LOCALE = "locale"
FIELD_FIELD = "field"
FIELD_LOCALIZED_SLIDES = "localized_slides"
PAYLOAD_KEY_PREFIX = "presentation_"

PROMPT_VERSION_V2 = "v2"
VAR_VIOLATIONS = "violations"

LOG_CONTENT_AUTOREPAIRED = "autopilot_content_autorepaired"
LOG_GATE_REPAIR_NOOP = "autopilot_gate_repair_noop"
LOG_GATE_REPAIR_CONFLICT = "autopilot_gate_repair_conflict"
LOG_FIELD_FIXED_RULES = "fixed_rules"
LOG_FIELD_REMAINING_RULES = "remaining_rules"
LOG_FIELD_NEXT_ACTION = "next_action"
