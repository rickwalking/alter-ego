"""Drop a carousel's approval when slide 1 changes (``ReviewReopener``).

Pedro's decision (2026-11-02): a cover switch on an approved (or scheduled)
carousel sends it back to final review. Two stores hold the approval:

1. the LangGraph checkpoint, parked at ``approved_hold``: it is resumed with
   ``reopen_review`` and waits at the ``final_review`` interrupt again;
2. the ``carousel_projects`` row every publish path reads
   (``workflow_status``): it becomes a draft at ``final_review /
   awaiting_human``, flushed in the caller's transaction, so it commits with
   the slide-1 write and the needs-republish marker.

The checkpoint goes first. If the row write then fails, the checkpoint asks
for a review of a carousel still approved with its old slide 1 (an approve
just approves it again); the other order could leave a dropped approval whose
checkpoint still reads approved.
"""

from __future__ import annotations

import typing
from collections.abc import Callable
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

if typing.TYPE_CHECKING:
    from rag_backend.application.services.carousel.editorial_workflow_service import (
        EditorialWorkflowService,
    )


class CheckpointReopener(Protocol):
    """Sends an approved carousel's graph back to the final-review interrupt."""

    async def reopen(self, project_id: str) -> bool:
        """True when a held checkpoint was reopened."""
        ...


class WorkflowCheckpointReopener:
    """The reopen through the editorial workflow service (its checkpointer)."""

    def __init__(self, workflows: Callable[[], EditorialWorkflowService]) -> None:
        self._workflows = workflows

    async def reopen(self, project_id: str) -> bool:
        """Resume the approved hold with ``reopen_review``."""
        return await self._workflows().reopen_final_review(project_id)


class ApprovalReopen:
    """``ReviewReopener`` on one session: checkpoint, then the row (flush)."""

    def __init__(self, session: AsyncSession, checkpoint: CheckpointReopener) -> None:
        self._session = session
        self._checkpoint = checkpoint

    async def reopen(self, project_id: str) -> None:
        """Reopen the checkpoint, then stage the draft row (the caller commits)."""
        from rag_backend.modules.editorial.infrastructure import (
            CarouselProjectWriteOwner,
        )

        await self._checkpoint.reopen(project_id)
        await CarouselProjectWriteOwner(self._session).reopen_final_review(project_id)


__all__ = ["ApprovalReopen", "CheckpointReopener", "WorkflowCheckpointReopener"]
