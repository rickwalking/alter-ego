"""Attribute panel rows to their current carousel project and running heartbeat."""

from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.queue_board import GenerationRow
from rag_backend.modules.editorial.public import (
    ProjectQueueMetadata,
    project_queue_metadata,
)
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.queue_constants import GENERATION_STATUS_RUNNING


@dataclass(frozen=True, kw_only=True)
class _ProjectContext:
    attribution: dict[str, str | None]
    projects: dict[str, ProjectQueueMetadata]


class QueueBoardProjects:
    """Read project identity once and never substitute generation update time."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enrich(self, rows: list[GenerationRow]) -> list[GenerationRow]:
        """Attach project phase, lock and running-only heartbeat to each row."""
        attribution = await self._attribution(rows)
        project_ids = {
            _project_id(row, attribution)
            for row in rows
            if _project_id(row, attribution) is not None
        }
        projects = await self._projects(project_ids)
        context = _ProjectContext(attribution=attribution, projects=projects)
        return [_project_row(row, context) for row in rows]

    async def _attribution(self, rows: list[GenerationRow]) -> dict[str, str | None]:
        run_ids = tuple(dict.fromkeys(row.autopilot_run_id for row in rows))
        ids = [UUID(run_id) for run_id in run_ids if run_id is not None]
        if not ids:
            return {}
        result = await self._session.execute(
            select(AutopilotRunModel.id, AutopilotRunModel.carousel_project_id).where(
                AutopilotRunModel.id.in_(ids)
            )
        )
        return {str(run_id): project_id for run_id, project_id in result.all()}

    async def _projects(self, ids: set[str | None]) -> dict[str, ProjectQueueMetadata]:
        present = {project_id for project_id in ids if project_id is not None}
        return await project_queue_metadata(self._session, present)


def _project_row(row: GenerationRow, context: _ProjectContext) -> GenerationRow:
    project_id = _project_id(row, context.attribution)
    project = context.projects.get(project_id or "")
    if project is None:
        return replace(
            row,
            carousel_project_id=project_id,
            run_heartbeat_at=None,
            lock_version=None,
        )
    heartbeat = project.heartbeat_at if _running(row) else None
    phase = row.last_phase or (None if row.staged else project.current_phase)
    return replace(
        row,
        carousel_project_id=project_id,
        last_phase=phase,
        run_heartbeat_at=heartbeat,
        lock_version=int(project.lock_version or 1),
    )


def _project_id(row: GenerationRow, attribution: dict[str, str | None]) -> str | None:
    attributed = attribution.get(row.autopilot_run_id or "")
    return attributed or row.carousel_project_id


def _running(row: GenerationRow) -> bool:
    return row.status == GENERATION_STATUS_RUNNING


__all__ = ["QueueBoardProjects"]
