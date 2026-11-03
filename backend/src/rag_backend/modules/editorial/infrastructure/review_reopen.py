"""Drop a carousel's approval when slide 1 changes (``ReviewReopener``).

Pedro's decision (2026-11-02): a cover switch on an approved (or scheduled)
carousel sends it back to final review. Two stores hold the approval:

1. the LangGraph checkpoint, parked at ``approved_hold``: it is resumed with
   ``reopen_review`` and waits at the ``final_review`` interrupt again;
2. the ``carousel_projects`` row every publish path reads
   (``workflow_status``): it becomes a draft at ``final_review /
   awaiting_human``, flushed in the caller's transaction, so it commits with
   the slide-1 write and the needs-republish marker.

Under the row lock the row is first re-checked (still approved, not
released), so a release that landed since the caller's read is never
rewritten; a checkpoint that cannot wait at the final review refuses too, so
the row and the checkpoint never disagree. The checkpoint then goes first. If
the row write then fails, the checkpoint asks
for a review of a carousel still approved with its old slide 1 (an approve
just approves it again); the other order could leave a dropped approval whose
checkpoint still reads approved.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.cover_switch_guard import (
    ReopenRefusedError,
    ReviewState,
    reopen_refusal,
    reopens_review,
)
from rag_backend.domain.constants.cover_review_switch import (
    REASON_AUTO_SELECT_PUBLISHED,
    REASON_REVIEW_NOT_REOPENED,
)


class CheckpointReopener(Protocol):
    """Sends an approved carousel's graph back to the final-review interrupt."""

    async def reopen(self, project_id: str) -> bool:
        """True when a held checkpoint was reopened."""
        ...


class CheckpointEngineReopener:
    """The reopen on the app's LangGraph checkpointer (None: nothing reopens)."""

    def __init__(self, checkpointer: object | None) -> None:
        self._checkpointer = checkpointer

    async def reopen(self, project_id: str) -> bool:
        """Resume the approved hold with ``reopen_review``."""
        from rag_backend.agents.carousel_workflow_engine import (
            CarouselWorkflowEngine,
        )

        engine = CarouselWorkflowEngine(checkpointer=self._checkpointer)
        return await engine.reopen_final_review(project_id)


class ApprovalReopen:
    """``ReviewReopener`` on one session: re-check under the row lock, the
    checkpoint, then the row (flush)."""

    def __init__(self, session: AsyncSession, checkpoint: CheckpointReopener) -> None:
        self._session = session
        self._checkpoint = checkpoint

    async def reopen(self, project_id: str) -> None:
        """Refuse a released or unapproved row, or a checkpoint that cannot
        reopen (``ReopenRefusedError``, nothing written); else stage the draft
        row (the caller commits)."""
        from rag_backend.modules.editorial.infrastructure import (
            CarouselProjectWriteOwner,
        )

        await _refuse_unless_approved(self._session, project_id)
        if not await self._checkpoint.reopen(project_id):
            raise ReopenRefusedError(REASON_REVIEW_NOT_REOPENED)
        await CarouselProjectWriteOwner(self._session).reopen_final_review(project_id)


async def _refuse_unless_approved(session: AsyncSession, project_id: str) -> None:
    """The approval and release read ``FOR UPDATE`` (a release waits on it)."""
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel as Row,
    )

    found = (
        await session.execute(
            select(Row.workflow_status, Row.is_public)
            .where(Row.id == project_id)
            .with_for_update()
        )
    ).one_or_none()
    if found is None:
        raise ReopenRefusedError(REASON_REVIEW_NOT_REOPENED)
    state = ReviewState(
        workflow_status=str(found.workflow_status or ""),
        is_public=bool(found.is_public),
    )
    if reopen_refusal(state) is not None:
        raise ReopenRefusedError(REASON_AUTO_SELECT_PUBLISHED)
    if not reopens_review(state):
        raise ReopenRefusedError(REASON_REVIEW_NOT_REOPENED)


__all__ = ["ApprovalReopen", "CheckpointEngineReopener", "CheckpointReopener"]
