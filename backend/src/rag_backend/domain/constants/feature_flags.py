"""Feature flag names for gradual rollout (DEPLOY-003)."""

FLAG_EDITORIAL_WORKFLOW = "editorial_workflow"
FLAG_QUALITY_CHECKS = "quality_checks"
FLAG_WORKFLOW_BOARD = "workflow_board"
FLAG_CONTENT_CALENDAR = "content_calendar"
FLAG_PALETTE_CATALOG = "palette_catalog"

ERR_FEATURE_DISABLED = "feature_disabled"

__all__ = [
    "ERR_FEATURE_DISABLED",
    "FLAG_CONTENT_CALENDAR",
    "FLAG_EDITORIAL_WORKFLOW",
    "FLAG_PALETTE_CATALOG",
    "FLAG_QUALITY_CHECKS",
    "FLAG_WORKFLOW_BOARD",
]
