"""Editorial-side implementation of the presentation progress callback (AE-0121).

The presentation image node reports image-generation progress through the
``WorkflowProgressPort`` callback (defined in the presentation module). EDITORIAL
owns the workflow-state ``phase_progress`` column (AE-0105 §2.3) and the SSE
progress channel, so the concrete callback lives here on the editorial side and
performs the byte-identical persist + publish the legacy in-node write did.

Dependency direction: editorial → presentation. This module imports the
presentation :class:`ProgressSnapshot` value object through the public facade and
implements the reporter; the presentation node depends only on its own port.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.editorial_workflow_support import (
    publish_workflow_progress,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.modules.presentation import ProgressSnapshot


class EditorialProgressReporter:
    """Persist the workflow ``phase_progress`` + publish it to the SSE stream.

    Constructed by the editorial image path with the request-scoped repository and
    the mutable project being rendered. On each reported snapshot it stamps the
    project's ``phase_progress`` (byte-identical to the legacy in-node payload),
    persists it through the repository (re-binding the returned project), and
    broadcasts the SSE progress event — exactly the steps the legacy
    ``_publish_progress_state`` ran, now owned by editorial.
    """

    def __init__(
        self,
        repository: CarouselRepository,
        project: CarouselProject,
    ) -> None:
        self._repository = repository
        self._project = project

    async def report_progress(self, snapshot: ProgressSnapshot) -> None:
        """Stamp + persist ``phase_progress`` and broadcast the SSE event."""
        self._project.phase_progress = snapshot.as_phase_progress()
        self._project = await self._repository.update_project(self._project)
        await publish_workflow_progress(
            snapshot.project_id,
            snapshot.sse_phase,
            dict(self._project.phase_progress or {}),
        )


__all__ = ["EditorialProgressReporter"]
