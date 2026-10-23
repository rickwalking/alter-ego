"""Constants for the quality rubric a carousel is generated and scored against.

The owner picks a rubric per carousel in the create wizard; a carousel created
without one (and every autopilot or chat-created carousel) gets the default
carousel rubric. Its criteria are
appended to every content-draft prompt, and once the drafts exist one judge call
scores each criterion on 0-100. The scores land in the workflow state's
``rubric_scores`` and in one ``rubric_evaluation_scores`` row per carousel.
"""

from __future__ import annotations

from typing import Final

RUBRIC_CONTENT_TYPE_CAROUSEL: Final = "carousel"
RUBRIC_SCORE_SCALE: Final = 100

RUBRIC_PROMPT_DOMAIN: Final = "carousel_rubric"
RUBRIC_PROMPT_VERSION: Final = "v1"
RUBRIC_PROMPT_CRITERIA: Final = "content_criteria"
RUBRIC_PROMPT_EVALUATE: Final = "evaluate"

STATE_KEY_RUBRIC_SCORES: Final = "rubric_scores"
STATE_KEY_CONTENT_HASH: Final = "content_hash"

RUBRIC_JUDGE_TIMEOUT_SECONDS: Final = 90.0
RUBRIC_MAX_CRITERIA: Final = 12
RUBRIC_CRITERION_TEXT_MAX_CHARS: Final = 1000
RUBRIC_CRITERION_NAME_MAX_CHARS: Final = 200

ERR_RUBRIC_NOT_FOUND: Final = "rubric_not_found"
ERR_RUBRIC_NOT_FOR_CAROUSELS: Final = "rubric_not_for_carousels"
ERR_RUBRIC_IN_USE: Final = "rubric_in_use"
ERR_RUBRIC_SCORES_INVALID: Final = "rubric_scores_invalid"

LOG_EVENT_RUBRIC_SCORED: Final = "carousel_rubric_scored"
LOG_EVENT_RUBRIC_SCORING_FAILED: Final = "carousel_rubric_scoring_failed"
LOG_EVENT_RUBRIC_SCORING_SKIPPED: Final = "carousel_rubric_scoring_skipped"

__all__ = [
    "ERR_RUBRIC_IN_USE",
    "ERR_RUBRIC_NOT_FOR_CAROUSELS",
    "ERR_RUBRIC_NOT_FOUND",
    "ERR_RUBRIC_SCORES_INVALID",
    "LOG_EVENT_RUBRIC_SCORED",
    "LOG_EVENT_RUBRIC_SCORING_FAILED",
    "LOG_EVENT_RUBRIC_SCORING_SKIPPED",
    "RUBRIC_CONTENT_TYPE_CAROUSEL",
    "RUBRIC_CRITERION_NAME_MAX_CHARS",
    "RUBRIC_CRITERION_TEXT_MAX_CHARS",
    "RUBRIC_JUDGE_TIMEOUT_SECONDS",
    "RUBRIC_MAX_CRITERIA",
    "RUBRIC_PROMPT_CRITERIA",
    "RUBRIC_PROMPT_DOMAIN",
    "RUBRIC_PROMPT_EVALUATE",
    "RUBRIC_PROMPT_VERSION",
    "RUBRIC_SCORE_SCALE",
    "STATE_KEY_CONTENT_HASH",
    "STATE_KEY_RUBRIC_SCORES",
]
