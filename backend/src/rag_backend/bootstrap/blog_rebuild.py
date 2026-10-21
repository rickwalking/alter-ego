"""Composition root of the hidden-post rebuild script.

Wires the application service (:class:`BlogRebuildService`) to its concrete
collaborators: the SQL candidate/attempt store, the carousel material source
(project + slides + persona + checkpoint state) and the generation
service. The CLI script imports this builder instead of the container directly.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from rag_backend.agents.carousel_workflow_engine import CarouselWorkflowEngine
from rag_backend.application.services.blog.blog_rebuild import (
    BlogRebuildService,
    RebuildDeps,
)
from rag_backend.bootstrap.blog_generation import (
    build_generation_service,
    resolve_persona,
)
from rag_backend.infrastructure.database.blog_rebuild_materials import (
    MaterialDeps,
    SqlCarouselMaterialSource,
)
from rag_backend.infrastructure.database.blog_rebuild_store import SqlBlogRebuildStore
from rag_backend.infrastructure.database.config import get_session_maker

_REBUILD_STATE_FIELDS = ("research_findings", "outline")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_lease() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class WorkflowStateReader:
    """Reads the small slice of the checkpoint a brief needs."""

    engine: CarouselWorkflowEngine

    async def __call__(self, project_id: str) -> Mapping[str, object] | None:
        """The checkpoint state, or ``None`` when there is no run for the project."""
        state = await self.engine.get_state(project_id)
        if state is None:
            return None
        values: Mapping[str, object] = dict(state)
        return {key: values[key] for key in _REBUILD_STATE_FIELDS if key in values}


def build_rebuild_service(
    checkpointer: object | None,
) -> BlogRebuildService:
    """Wire the rebuild service for one script run."""
    sessions = get_session_maker()
    materials = SqlCarouselMaterialSource(
        MaterialDeps(
            sessions=sessions,
            workflow_state=WorkflowStateReader(CarouselWorkflowEngine(checkpointer)),
            resolve_persona=resolve_persona,
        )
    )
    return BlogRebuildService(
        RebuildDeps(
            store=SqlBlogRebuildStore(sessions),
            materials=materials,
            service_factory=build_generation_service,
            clock=_now_iso,
            new_lease=_new_lease,
        )
    )


__all__ = ["WorkflowStateReader", "build_rebuild_service"]
