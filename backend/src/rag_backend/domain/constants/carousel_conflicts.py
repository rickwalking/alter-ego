"""Typed conflict codes for carousel 409 responses (AE-0316).

The three legacy resume conflict causes keep their historical detail strings
as their machine-readable codes so existing clients (which string-compare
``detail``) are unaffected; new conflict causes get new codes. The structured
payload rides alongside the legacy ``detail`` string in the response body —
see ``api/middleware/carousel_conflict_handler.py``.
"""

from rag_backend.domain.constants.carousel_workflow import (
    ERR_RESUME_ALREADY_IN_PROGRESS,
    ERR_REVISION_CAP_EXCEEDED,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT

CONFLICT_CODE_RUN_IN_PROGRESS = ERR_RESUME_ALREADY_IN_PROGRESS
CONFLICT_CODE_VERSION_CONFLICT = ERR_VERSION_CONFLICT
CONFLICT_CODE_REVISION_CAP_EXCEEDED = ERR_REVISION_CAP_EXCEEDED
CONFLICT_CODE_BUILD_IN_PROGRESS = "build_in_progress"
CONFLICT_CODE_MUTATION_IN_PROGRESS = "mutation_in_progress"

CAROUSEL_CONFLICT_CODES = (
    CONFLICT_CODE_RUN_IN_PROGRESS,
    CONFLICT_CODE_VERSION_CONFLICT,
    CONFLICT_CODE_REVISION_CAP_EXCEEDED,
    CONFLICT_CODE_BUILD_IN_PROGRESS,
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
)

MSG_RUN_IN_PROGRESS = "A workflow run is already in progress for this carousel."
MSG_VERSION_CONFLICT = "The carousel changed since it was loaded; refresh and retry."
MSG_REVISION_CAP_EXCEEDED = (
    "The revision limit for this phase is exhausted; edit the text directly "
    "instead of requesting another revision."
)
MSG_BUILD_IN_PROGRESS = "An artifact build is already running for this carousel."
MSG_MUTATION_IN_PROGRESS = (
    "Another operation is modifying this carousel; retry in a moment."
)

CONFLICT_MESSAGES: dict[str, str] = {
    CONFLICT_CODE_RUN_IN_PROGRESS: MSG_RUN_IN_PROGRESS,
    CONFLICT_CODE_VERSION_CONFLICT: MSG_VERSION_CONFLICT,
    CONFLICT_CODE_REVISION_CAP_EXCEEDED: MSG_REVISION_CAP_EXCEEDED,
    CONFLICT_CODE_BUILD_IN_PROGRESS: MSG_BUILD_IN_PROGRESS,
    CONFLICT_CODE_MUTATION_IN_PROGRESS: MSG_MUTATION_IN_PROGRESS,
}

__all__ = [
    "CAROUSEL_CONFLICT_CODES",
    "CONFLICT_CODE_BUILD_IN_PROGRESS",
    "CONFLICT_CODE_MUTATION_IN_PROGRESS",
    "CONFLICT_CODE_REVISION_CAP_EXCEEDED",
    "CONFLICT_CODE_RUN_IN_PROGRESS",
    "CONFLICT_CODE_VERSION_CONFLICT",
    "CONFLICT_MESSAGES",
    "MSG_BUILD_IN_PROGRESS",
    "MSG_MUTATION_IN_PROGRESS",
    "MSG_REVISION_CAP_EXCEEDED",
    "MSG_RUN_IN_PROGRESS",
    "MSG_VERSION_CONFLICT",
]
