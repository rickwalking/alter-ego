"""Load a candidate row's carousel inputs for the hidden-post rebuild.

Composes the carousel brief material from the persisted project and
slides, the persona, and the workflow checkpoint's research/outline. Reads only:
a missing project (or project id) is ``None`` so the service reports a skip.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, replace
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_backend.application.services.blog.blog_brief import CarouselMaterial
from rag_backend.application.services.blog.blog_rebuild import RebuildCandidate
from rag_backend.application.services.blog.blog_section_plan import (
    SectionCountSource,
    resolve_section_count,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.domain.protocols.repositories import CarouselRepository
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)

SessionFactory = async_sessionmaker[AsyncSession]
WorkflowStateReader = Callable[[str], Awaitable[Mapping[str, object] | None]]
PersonaResolver = Callable[
    [AsyncSession, tuple[str | None, ...]], Awaitable[PersonaProfile]
]


@dataclass(frozen=True)
class MaterialDeps:
    """How to read a candidate's carousel (all injected for testing)."""

    sessions: SessionFactory
    workflow_state: WorkflowStateReader
    resolve_persona: PersonaResolver


def _project_uuid(candidate: RebuildCandidate) -> UUID | None:
    if candidate.project_id is None:
        return None
    try:
        return UUID(candidate.project_id)
    except ValueError:
        return None


class SqlCarouselMaterialSource:
    """``CarouselMaterialSource`` over the carousel tables + checkpoint."""

    def __init__(self, deps: MaterialDeps) -> None:
        self._deps = deps

    async def load(self, candidate: RebuildCandidate) -> CarouselMaterial | None:
        """The candidate's carousel material, or ``None`` when it is gone."""
        project_id = _project_uuid(candidate)
        if project_id is None:
            return None
        async with self._deps.sessions() as session:
            material = await self._read(session, project_id)
        if material is None:
            return None
        state = await self._deps.workflow_state(candidate.project_id or "")
        return replace(material, state=state)

    async def _read(
        self, session: AsyncSession, project_id: UUID
    ) -> CarouselMaterial | None:
        repo: CarouselRepository = PostgresCarouselRepository(session)
        project = await repo.get_project_by_id(project_id)
        if project is None:
            return None
        slides = await repo.get_slides_by_project(project_id)
        persona = await self._deps.resolve_persona(session, (project.persona_id,))
        return CarouselMaterial(
            title=project.title or project.topic,
            topic=project.topic,
            persona=persona,
            section_count=resolve_section_count(
                SectionCountSource(
                    project.slide_count,
                    len(slides),
                    project.slides_config,
                    project.content_mode,
                )
            ),
            slides=tuple(slides),
        )


__all__ = ["MaterialDeps", "SqlCarouselMaterialSource"]
