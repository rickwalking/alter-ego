"""SQLAlchemy adapter for browser-observed X signals.

Upserts each accepted post, then reuses the topic-intake allowlist helper
so a later topic may cite the canonical URL. The caller owns the commit.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.ports import RecordServedUrls
from rag_backend.modules.autopilot.domain.scout_ports import SaveXSignals
from rag_backend.modules.autopilot.domain.x_observation import AcceptedObservation
from rag_backend.modules.autopilot.infrastructure.intake_store import (
    SqlAlchemyTopicIntakeStore,
)
from rag_backend.modules.autopilot.infrastructure.models import XBrowserSignalModel


class SqlAlchemyXSignalStore:
    """Session-scoped store. Structurally an ``XSignalStore``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._allowlist = SqlAlchemyTopicIntakeStore(session)

    async def save(self, command: SaveXSignals) -> None:
        """Upsert the signals, then refresh their served-URL rows."""
        for item in command.rows:
            await self._upsert(item, command.stored_at)
        await self._session.flush()
        urls = tuple(item.url for item in command.rows)
        await self._allowlist.record_served_urls(
            RecordServedUrls(urls=urls, served_at=command.stored_at)
        )

    async def commit(self) -> None:
        """Commit the current unit of work."""
        await self._session.commit()

    async def _upsert(self, item: AcceptedObservation, stored_at: datetime) -> None:
        existing = await self._session.get(XBrowserSignalModel, item.url)
        if existing is None:
            self._session.add(_row(item, stored_at))
            return
        _copy(existing, item, stored_at)


def _row(item: AcceptedObservation, stored_at: datetime) -> XBrowserSignalModel:
    return XBrowserSignalModel(
        url=item.url,
        handle=item.handle,
        text=item.text,
        likes=item.likes,
        reposts=item.reposts,
        replies=item.replies,
        views=item.views,
        observed_at=item.observed_at,
        posted_at=item.posted_at,
        source=item.source.value,
        stored_at=stored_at,
    )


def _copy(
    row: XBrowserSignalModel, item: AcceptedObservation, stored_at: datetime
) -> None:
    row.handle = item.handle
    row.text = item.text
    row.likes = item.likes
    row.reposts = item.reposts
    row.replies = item.replies
    row.views = item.views
    row.observed_at = item.observed_at
    row.posted_at = item.posted_at
    row.source = item.source.value
    row.stored_at = stored_at
