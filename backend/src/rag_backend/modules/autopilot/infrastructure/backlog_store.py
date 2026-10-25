"""``BacklogStore`` on the caller's session: backlog themes are topic candidates.

Status moves are compare-and-set on the waiting statuses, so a "Gerar agora" tap
and the next intake never queue the same theme twice. Nothing here commits.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import CursorResult, Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.backlog import (
    BacklogChange,
    BacklogTheme,
    BacklogWindow,
    GenerateNowCommand,
    expiry_cutoff,
)
from rag_backend.modules.autopilot.domain.ports import QueuedRunCommand
from rag_backend.modules.autopilot.domain.topic_text import as_utc
from rag_backend.modules.autopilot.infrastructure.intake_store import (
    SqlAlchemyTopicIntakeStore,
)
from rag_backend.modules.autopilot.infrastructure.models import TopicCandidateModel
from rag_backend.modules.autopilot.queue_constants import (
    BACKLOG_MAX,
    BACKLOG_WAITING,
    CANDIDATE_BACKLOG,
    CANDIDATE_GENERATE_NOW,
)

_T = TopicCandidateModel


def _themes() -> Select[tuple[UUID, str, datetime]]:
    return select(_T.id, _T.title, _T.created_at).order_by(_T.created_at, _T.id)


class SqlBacklogStore:
    """Implements ``BacklogStore``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def waiting(self, window: BacklogWindow) -> list[BacklogTheme]:
        """Waiting themes stored in the window, oldest first."""
        return await self._read(
            _themes().where(
                _T.status.in_(BACKLOG_WAITING),
                _T.created_at >= window.since,
                _T.created_at < window.before,
            )
        )

    async def change(self, change: BacklogChange) -> tuple[UUID, ...]:
        """Compare-and-set the status; the ids that actually moved."""
        if not change.candidate_ids:
            return ()
        result = await self._session.execute(
            update(_T)
            .where(_T.id.in_(change.candidate_ids), _T.status.in_(change.expected))
            .values(status=change.status)
            .returning(_T.id)
        )
        return tuple(result.scalars().all())

    async def unannounced(self) -> list[BacklogTheme]:
        """Themes that joined the backlog and were not announced yet."""
        return await self._read(
            _themes().where(_T.status == CANDIDATE_BACKLOG).limit(BACKLOG_MAX)
        )

    async def generate_now(self, command: GenerateNowCommand) -> BacklogTheme | None:
        """Take a waiting theme out of the backlog and queue its run, once."""
        result = await self._session.execute(
            update(_T)
            .where(
                _T.id == command.candidate_id,
                _T.status.in_(BACKLOG_WAITING),
                _T.created_at >= expiry_cutoff(command.created_at),
            )
            .values(status=CANDIDATE_GENERATE_NOW)
        )
        if cast(CursorResult[object], result).rowcount != 1:
            return None
        await SqlAlchemyTopicIntakeStore(self._session).add_queued_run(
            QueuedRunCommand(
                run_id=command.run_id,
                topic_candidate_id=command.candidate_id,
                created_at=command.created_at,
            )
        )
        themes = await self._read(_themes().where(_T.id == command.candidate_id))
        return themes[0] if themes else None

    async def _read(
        self, statement: Select[tuple[UUID, str, datetime]]
    ) -> list[BacklogTheme]:
        result = await self._session.execute(statement)
        return [
            BacklogTheme(candidate_id=row[0], title=row[1], created_at=as_utc(row[2]))
            for row in result.all()
        ]


__all__ = ["SqlBacklogStore"]
