"""Constants for using an autopilot-generated cover on slide 1.

When the cover generation the autopilot started for a fresh carousel
succeeds, the cover becomes slide 1's ``slide_cover`` (kind ``ai_image``)
while the workflow is paused at a gate, unless the owner chose a cover in the
meantime. Every refusal is a logged skip with one of the reasons below.
"""

from __future__ import annotations

AUTO_SELECT_POLL_SECONDS = 5.0
AUTO_SELECT_MAX_WAIT_SECONDS = 45 * 60.0

LOG_COVER_AUTO_SELECT = "autopilot_cover_auto_select"

OUTCOME_AUTO_SELECT_SELECTED = "selected"
OUTCOME_AUTO_SELECT_ALREADY = "already_selected"
OUTCOME_AUTO_SELECT_SKIPPED = "skipped"
OUTCOME_AUTO_SELECT_CRASHED = "crashed"

REASON_AUTO_SELECT_NO_RESULT = "no_result"
REASON_AUTO_SELECT_NO_PROJECT = "no_project"
REASON_AUTO_SELECT_COMPLETED = "carousel_completed"
REASON_AUTO_SELECT_FAILED = "carousel_failed"
REASON_AUTO_SELECT_TIMED_OUT = "timed_out"
REASON_AUTO_SELECT_OWNER_COVER = "owner_cover"
REASON_AUTO_SELECT_MANUAL_CHOICE = "manual_choice"
REASON_AUTO_SELECT_ASSET_GONE = "asset_gone"
REASON_AUTO_SELECT_CONFLICT = "conflict"

__all__ = [
    "AUTO_SELECT_MAX_WAIT_SECONDS",
    "AUTO_SELECT_POLL_SECONDS",
    "LOG_COVER_AUTO_SELECT",
    "OUTCOME_AUTO_SELECT_ALREADY",
    "OUTCOME_AUTO_SELECT_CRASHED",
    "OUTCOME_AUTO_SELECT_SELECTED",
    "OUTCOME_AUTO_SELECT_SKIPPED",
    "REASON_AUTO_SELECT_ASSET_GONE",
    "REASON_AUTO_SELECT_COMPLETED",
    "REASON_AUTO_SELECT_CONFLICT",
    "REASON_AUTO_SELECT_FAILED",
    "REASON_AUTO_SELECT_MANUAL_CHOICE",
    "REASON_AUTO_SELECT_NO_PROJECT",
    "REASON_AUTO_SELECT_NO_RESULT",
    "REASON_AUTO_SELECT_OWNER_COVER",
    "REASON_AUTO_SELECT_TIMED_OUT",
]
