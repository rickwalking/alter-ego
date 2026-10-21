"""SQLAlchemy adapter for the ``instagram_stories`` row.

The publish claim serializes callers for one carousel, so a read-then-write
upsert is enough. The caller commits.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.publish import StoredContainer
from rag_backend.modules.autopilot.domain.story import (
    SaveStoryContainer,
    SaveStoryResult,
    StoryRecord,
)
from rag_backend.modules.autopilot.infrastructure.models import InstagramStoryModel
from rag_backend.modules.autopilot.infrastructure.run_mapping import aware
from rag_backend.modules.autopilot.story_constants import STORY_STATE_PENDING


class SqlStoryStore:
    """One row per carousel, keyed by ``carousel_project_id``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, project_id: str) -> StoryRecord | None:
        """Return the stored Story, or None."""
        row = await self._row(project_id)
        if row is None:
            return None
        return _record(row)

    async def save_container(self, command: SaveStoryContainer) -> None:
        """Store the container; the state stays ``pending`` until it is finished."""
        row = await self._row_or_new(command.project_id)
        row.state = STORY_STATE_PENDING
        row.story_container_id = command.container.container_id
        row.story_container_created_at = command.container.created_at
        row.updated_at = command.container.created_at
        await self._session.flush()

    async def save_result(self, command: SaveStoryResult) -> None:
        """Store the final state. A null media id does not clear a stored one."""
        row = await self._row_or_new(command.project_id)
        row.state = command.state
        row.error = command.error
        if command.media_id is not None:
            row.story_media_id = command.media_id
        row.updated_at = command.at
        await self._session.flush()

    async def _row(self, project_id: str) -> InstagramStoryModel | None:
        return await self._session.get(
            InstagramStoryModel, project_id, populate_existing=True
        )

    async def _row_or_new(self, project_id: str) -> InstagramStoryModel:
        row = await self._row(project_id)
        if row is not None:
            return row
        row = InstagramStoryModel(
            carousel_project_id=project_id, state=STORY_STATE_PENDING
        )
        self._session.add(row)
        return row


def _record(row: InstagramStoryModel) -> StoryRecord:
    return StoryRecord(
        project_id=row.carousel_project_id,
        state=row.state,
        container=_container(row),
        media_id=row.story_media_id,
        error=row.error,
    )


def _container(row: InstagramStoryModel) -> StoredContainer | None:
    created_at = aware(row.story_container_created_at)
    if not row.story_container_id or created_at is None:
        return None
    return StoredContainer(container_id=row.story_container_id, created_at=created_at)
