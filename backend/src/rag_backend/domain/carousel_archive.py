"""Whether a carousel may be archived (Pedro's decision)."""

from rag_backend.domain.constants.carousel_archive import (
    ARCHIVE_REFUSED_IN_PROGRESS,
    ARCHIVE_REFUSED_PUBLISHED,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_PUBLISHED,
    PHASE_STATUS_IN_PROGRESS,
)


def archive_refusal(current_phase: str | None, phase_status: str | None) -> str | None:
    """The refusal code for archiving a carousel in this state, or ``None`` if allowed.

    A published carousel is finished work, and a running phase must end first.
    """
    if current_phase == PHASE_PUBLISHED:
        return ARCHIVE_REFUSED_PUBLISHED
    if phase_status == PHASE_STATUS_IN_PROGRESS:
        return ARCHIVE_REFUSED_IN_PROGRESS
    return None
