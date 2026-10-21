"""Constants of the rebuild of hidden carousel-origin posts.

The durable hide marker lives under
``ai_generation_metadata.hidden_bad_post``. The rebuild adds ``rebuilt_at`` to
the **same** marker (it never deletes it), so the selection stays auditable and
a re-run is a no-op. Selection is independent of ``status``: hiding already set
``draft``, so a status-based selector would immediately go empty.

A run with no owner uses the rebuild actor for its audit entries (the row's author is
preferred). Partial image runs are stamped as rebuilt to bound regeneration cost; only a
``failed`` generation leaves ``rebuilt_at`` unset so a re-run retries it.
"""

from typing import Final

HIDDEN_BAD_POST_KEY: Final = "hidden_bad_post"
REBUILT_AT_KEY: Final = "rebuilt_at"
REBUILD_STATUS_KEY: Final = "rebuild_status"

REBUILD_ACTOR: Final = "system:ae-0426-rebuild"

CRITERION_MARKER: Final = "hidden_bad_post"
CRITERION_ALREADY_REBUILT: Final = "already_rebuilt"
CRITERION_V2_WITH_QUALITY: Final = "already_v2_with_quality"
CRITERION_MISSING_CAROUSEL: Final = "missing_carousel"
CRITERION_MISSING_NOTES: Final = "missing_notes"
CRITERION_CURRENTLY_PUBLISHED: Final = "currently_published"

OUTCOME_SELECTED: Final = "selected"
OUTCOME_REBUILT: Final = "rebuilt"
OUTCOME_SKIPPED: Final = "skipped"
OUTCOME_FAILED: Final = "failed"

REBUILT_OUTCOMES: Final[frozenset[str]] = frozenset({"complete", "partial"})

LOG_REBUILD_SELECTED: Final = "blog_rebuild_selected"
LOG_REBUILD_FINISHED: Final = "blog_rebuild_post_finished"
LOG_REBUILD_SKIPPED: Final = "blog_rebuild_post_skipped"
LOG_REBUILD_FAILED: Final = "blog_rebuild_post_failed"
LOG_REBUILD_CAPPED: Final = "blog_rebuild_selection_capped"
LOG_REBUILD_ABORTED: Final = "blog_rebuild_aborted"
LOG_REBUILD_SUMMARY: Final = "blog_rebuild_summary"

__all__ = [
    "CRITERION_ALREADY_REBUILT",
    "CRITERION_CURRENTLY_PUBLISHED",
    "CRITERION_MARKER",
    "CRITERION_MISSING_CAROUSEL",
    "CRITERION_MISSING_NOTES",
    "CRITERION_V2_WITH_QUALITY",
    "HIDDEN_BAD_POST_KEY",
    "LOG_REBUILD_ABORTED",
    "LOG_REBUILD_CAPPED",
    "LOG_REBUILD_FAILED",
    "LOG_REBUILD_FINISHED",
    "LOG_REBUILD_SELECTED",
    "LOG_REBUILD_SKIPPED",
    "LOG_REBUILD_SUMMARY",
    "OUTCOME_FAILED",
    "OUTCOME_REBUILT",
    "OUTCOME_SELECTED",
    "OUTCOME_SKIPPED",
    "REBUILD_ACTOR",
    "REBUILD_STATUS_KEY",
    "REBUILT_AT_KEY",
    "REBUILT_OUTCOMES",
]
