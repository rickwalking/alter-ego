"""Constants for the version history of a carousel's caption and LinkedIn posts.

Each saved change of the Instagram caption or a LinkedIn post (PT/EN) is a row
in ``content_versions`` with ``content_type = "carousel_copy"``, the carousel id
as ``content_id`` and ``snapshot = {field, text[, restored_from]}``. Versions are
numbered per carousel (the per-content unique index). A save also keeps the text
it replaced, with no author, whenever that text is not the newest stored one
(the generated text, or one another writer such as the chat refine left), so it
can be restored.
"""

from __future__ import annotations

from typing import Final

CONTENT_TYPE_CAROUSEL_COPY: Final = "carousel_copy"

SNAPSHOT_FIELD_KEY: Final = "field"
SNAPSHOT_TEXT_KEY: Final = "text"
SNAPSHOT_RESTORED_FROM_KEY: Final = "restored_from"

SUMMARY_EDIT: Final = "edit"
SUMMARY_PREVIOUS: Final = "previous"
SUMMARY_RESTORE: Final = "restore"

VERSIONS_PAGE_DEFAULT: Final = 50
VERSIONS_PAGE_MAX: Final = 200

ERR_COPY_VERSION_NOT_FOUND: Final = "copy_version_not_found"

__all__ = [
    "CONTENT_TYPE_CAROUSEL_COPY",
    "ERR_COPY_VERSION_NOT_FOUND",
    "SNAPSHOT_FIELD_KEY",
    "SNAPSHOT_RESTORED_FROM_KEY",
    "SNAPSHOT_TEXT_KEY",
    "SUMMARY_EDIT",
    "SUMMARY_PREVIOUS",
    "SUMMARY_RESTORE",
    "VERSIONS_PAGE_DEFAULT",
    "VERSIONS_PAGE_MAX",
]
