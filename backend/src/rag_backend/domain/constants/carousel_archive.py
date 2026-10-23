"""Constants of the carousel archive (Pedro's decision: owner and auto-archive)."""

ARCHIVE_REFUSED_IN_PROGRESS = "in_progress"
"""Refusal code: the carousel's phase is running."""

ARCHIVE_REFUSED_PUBLISHED = "published"
"""Refusal code: a published carousel stays on the board."""

ERR_ARCHIVE_IN_PROGRESS = (
    "The carousel cannot be archived while its phase is in progress"
)
ERR_ARCHIVE_PUBLISHED = "A published carousel cannot be archived"

CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS = 30
"""Days without activity before the workflow worker archives a carousel."""

AUTO_ARCHIVE_LOG_EVENT = "carousel_auto_archived"
