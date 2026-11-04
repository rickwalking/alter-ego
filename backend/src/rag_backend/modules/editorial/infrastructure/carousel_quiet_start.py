"""A run start written inside a caller's transaction, announced after its commit.

The owner Retry flips the carousel to ``in_progress`` as the last write of its
transaction (``stage``), and pushes the phase change and ``run.started`` to the
browser only once that transaction committed (``announce``). A Retry that rolls
back never shows a run that does not exist.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.infrastructure.carousel_automation import (
    EditorialWorkflowEngine,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_write_owner import (
    CarouselProjectWriteOwner,
)


class QuietRunStart:
    """Stage the ``in_progress`` flip; announce it after the commit."""

    def __init__(self, engine: EditorialWorkflowEngine, session: AsyncSession) -> None:
        self._engine = engine
        self._session = session

    async def stage(self, project_id: str) -> str:
        """Flip the row to ``in_progress`` (flush only, no event); return the phase."""
        from rag_backend.application.services.carousel.resume_in_progress import (
            in_progress_state,
        )

        prior = await self._engine.get_workflow_state(project_id)
        state = in_progress_state(prior, project_id)
        await CarouselProjectWriteOwner(self._session).sync_phase(project_id, state)
        return str(state.get("current_phase", ""))

    async def announce(self, project_id: str, phase: str) -> None:
        """Publish the phase change and ``run.started``; call after the commit."""
        from rag_backend.application.services.carousel import (
            editorial_workflow_run_events as run_events,
        )
        from rag_backend.application.services.carousel import (
            editorial_workflow_sse_publish as sse,
        )

        await sse.publish_workflow_phase_change(
            project_id, phase, PHASE_STATUS_IN_PROGRESS
        )
        row = await self._session.get(CarouselProjectModel, project_id)
        started = row.run_started_at if row is not None else None
        await run_events.publish_run_started(project_id, phase, started)


__all__ = ["QuietRunStart"]
