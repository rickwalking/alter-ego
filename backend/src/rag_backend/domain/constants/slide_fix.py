"""Constants for the autopilot model fix of failing slides (AE-0401).

After the deterministic gate repair, each slide that still fails a blocking
copy rule (or scores under the voice floor) is rewritten by the fast model,
at most ``AUTOFIX_MODEL_ATTEMPTS`` times, then the run escalates.
"""

from __future__ import annotations

# Owner decision 2026-10-16: three model attempts per slide, then escalate.
AUTOFIX_MODEL_ATTEMPTS = 3
SLIDE_FIX_TIMEOUT_SECONDS = 120.0

SLIDE_FIX_PROMPT_DOMAIN = "carousel"
SLIDE_FIX_PROMPT_NAME = "slide_fix"
SLIDE_FIX_PROMPT_VERSION = "v1"

# Prompt variables.
VAR_SLIDE_INDEX = "slide_index"
VAR_SLIDE_TYPE = "slide_type"
VAR_ROLE = "role"
VAR_SLIDE_JSON = "slide_json"
VAR_ISSUES = "issues"
VAR_STYLE_GUIDE = "style_guide"
VAR_HEADING_MAX = "heading_max_characters"
VAR_BODY_MAX = "body_max_characters"
VAR_VOICE_FLOOR = "voice_floor"
VAR_QUALITY_RUBRIC = "quality_rubric"

# Persona-score keys the content phase writes ("slide_3").
PERSONA_SCORE_SLIDE_KEY = "slide_{index}"

# Issue codes that are not presentation rules.
ISSUE_VOICE_SCORE_LOW = "voice_score_low"
ISSUE_VOICE_SCORE_MESSAGE = "Voice match score {score:.0f} is under {floor:.0f}"
ISSUE_MODEL_ERROR = "model_error"
ISSUE_MODEL_UNPARSEABLE = "model_output_unparseable"
ISSUE_LINE = "- {code} ({locale} {field}): {message}"

# Outcome of one model attempt.
ATTEMPT_FIXED = "fixed"
ATTEMPT_STILL_FAILING = "still_failing"
ATTEMPT_MODEL_ERROR = "model_error"
ATTEMPT_UNPARSEABLE = "unparseable"

LOG_SLIDE_FIX_APPLIED = "carousel_slide_fix_applied"
LOG_SLIDE_FIX_CONFLICT = "carousel_slide_fix_conflict"
LOG_SLIDE_FIX_NOOP = "carousel_slide_fix_noop"

__all__ = [
    "ATTEMPT_FIXED",
    "ATTEMPT_MODEL_ERROR",
    "ATTEMPT_STILL_FAILING",
    "ATTEMPT_UNPARSEABLE",
    "AUTOFIX_MODEL_ATTEMPTS",
    "ISSUE_LINE",
    "ISSUE_MODEL_ERROR",
    "ISSUE_MODEL_UNPARSEABLE",
    "ISSUE_VOICE_SCORE_LOW",
    "ISSUE_VOICE_SCORE_MESSAGE",
    "LOG_SLIDE_FIX_APPLIED",
    "LOG_SLIDE_FIX_CONFLICT",
    "LOG_SLIDE_FIX_NOOP",
    "PERSONA_SCORE_SLIDE_KEY",
    "SLIDE_FIX_PROMPT_DOMAIN",
    "SLIDE_FIX_PROMPT_NAME",
    "SLIDE_FIX_PROMPT_VERSION",
    "SLIDE_FIX_TIMEOUT_SECONDS",
    "VAR_BODY_MAX",
    "VAR_HEADING_MAX",
    "VAR_ISSUES",
    "VAR_QUALITY_RUBRIC",
    "VAR_ROLE",
    "VAR_SLIDE_INDEX",
    "VAR_SLIDE_JSON",
    "VAR_SLIDE_TYPE",
    "VAR_STYLE_GUIDE",
    "VAR_VOICE_FLOOR",
]
