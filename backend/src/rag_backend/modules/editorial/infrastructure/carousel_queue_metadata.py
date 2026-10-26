"""Read queue-facing project metadata through the editorial write model."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.domain.queue_metadata import ProjectQueueMetadata


async def project_queue_metadata(
    session: AsyncSession, project_ids: set[str]
) -> dict[str, ProjectQueueMetadata]:
    """Read current project phase, lock version and heartbeat once."""
    if not project_ids:
        return {}
    result = await session.scalars(
        select(CarouselProjectModel).where(CarouselProjectModel.id.in_(project_ids))
    )
    return {
        str(project.id): ProjectQueueMetadata(
            current_phase=str(project.current_phase or ""),
            lock_version=int(project.lock_version or 1),
            heartbeat_at=project.run_heartbeat_at,
        )
        for project in result.all()
    }


__all__ = ["project_queue_metadata"]
