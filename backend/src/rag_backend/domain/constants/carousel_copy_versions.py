"""Constants for the version history of a carousel's caption and LinkedIn posts.

Each saved change of the Instagram caption or a LinkedIn post (PT/EN) is a row
in ``content_versions`` with ``content_type = "carousel_copy"``, the carousel id
as ``content_id`` and ``snapshot = {field, text[, restored_from]}``. Versions are
numbered per carousel (the per-content unique index). The first change of a text
also keeps the text it replaced, with no author, so the generated text can be
restored.
"""

from __future__ import annotations

from typing import Final

CONTENT_TYPE_CAROUSEL_COPY: Final = "carousel_copy"

SNAPSHOT_FIELD_KEY: Final = "field"
SNAPSHOT_TEXT_KEY: Final = "text"
SNAPSHOT_RESTORED_FROM_KEY: Final = "restored_from"

SUMMARY_EDIT: Final = "edit"
SUMMARY_ORIGINAL: Final = "original"
SUMMARY_RESTORE: Final = "restore"

ERR_COPY_VERSION_NOT_FOUND: Final = "copy_version_not_found"

LOG_EVENT_COPY_VERSIONS_RECORDED: Final = "carousel_copy_versions_recorded"

__all__ = [
    "CONTENT_TYPE_CAROUSEL_COPY",
    "ERR_COPY_VERSION_NOT_FOUND",
    "LOG_EVENT_COPY_VERSIONS_RECORDED",
    "SNAPSHOT_FIELD_KEY",
    "SNAPSHOT_RESTORED_FROM_KEY",
    "SNAPSHOT_TEXT_KEY",
    "SUMMARY_EDIT",
    "SUMMARY_ORIGINAL",
    "SUMMARY_RESTORE",
]
