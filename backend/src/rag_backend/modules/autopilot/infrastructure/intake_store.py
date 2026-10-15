"""SQLAlchemy adapter for topic intake.

Records signal URLs when a bundle is served, then answers the allowlist,
dedupe, and daily-cap reads. The caller owns the commit.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.content_mode import CONTENT_MODE_NEWS_ANALYSIS
from rag_backend.modules.autopilot.constants import (
    RUN_ATTEMPTS_INITIAL,
    SERVED_URL_TTL_HOURS,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TopicCandidate,
)
from rag_backend.modules.autopilot.domain.ports import (
    DayWindow,
    HashLookup,
    QueuedRunCommand,
    RecordServedUrls,
)
from rag_backend.modules.autopilot.domain.x_status import canonical_url
from rag_backend.modules.autopilot.infrastructure.advisory_lock import (
    advisory_xact_lock,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    ServedSignalUrlModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.infrastructure.topic_rows import topic_row
from rag_backend.modules.autopilot.recovery_constants import INTAKE_LOCK_KEY
from rag_backend.modules.editorial.public import CarouselAutomationAcl


class SqlAlchemyTopicIntakeStore:
    """Session-scoped intake adapter. Structurally a ``TopicIntakeStore``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_served_urls(self, command: RecordServedUrls) -> None:
        """Refresh the given URLs, then delete rows outside the 6 hour window."""
        for url in _canonical_urls(command.urls):
            await self._upsert(url, command.served_at)
        await self._session.flush()
        cutoff = command.served_at - timedelta(hours=SERVED_URL_TTL_HOURS)
        await self._session.execute(
            delete(ServedSignalUrlModel).where(ServedSignalUrlModel.served_at < cutoff)
        )
        await self._session.flush()

    async def urls_served_since(self, since: datetime) -> frozenset[str]:
        """Return URLs last served at or after ``since``."""
        result = await self._session.execute(
            select(ServedSignalUrlModel.url).where(
                ServedSignalUrlModel.served_at >= since
            )
        )
        return frozenset(result.scalars().all())

    async def ids_for_hashes(self, query: HashLookup) -> dict[str, UUID]:
        """Return the candidate id for each hash that already exists."""
        if not query.hashes:
            return {}
        result = await self._session.execute(
            select(TopicCandidateModel).where(
                TopicCandidateModel.signal_hash.in_(query.hashes)
            )
        )
        return {row.signal_hash: row.id for row in result.scalars().all()}

    async def carousel_topics_since(self, since: datetime) -> tuple[str, ...]:
        """Return non-blank carousel topics created at or after ``since``."""
        return await CarouselAutomationAcl(self._session).topics_since(since)

    async def runs_created_between(self, window: DayWindow) -> int:
        """Count runs whose ``created_at`` is inside the half-open window."""
        result = await self._session.execute(
            select(func.count())
            .select_from(AutopilotRunModel)
            .where(
                AutopilotRunModel.created_at >= window.start,
                AutopilotRunModel.created_at < window.end,
            )
        )
        return int(result.scalar_one())

    async def news_runs_created_between(self, window: DayWindow) -> int:
        """AE-0377: Radar IA runs (topic mode NULL or news) in the window."""
        result = await self._session.execute(
            select(func.count())
            .select_from(AutopilotRunModel)
            .join(
                TopicCandidateModel,
                TopicCandidateModel.id == AutopilotRunModel.topic_candidate_id,
            )
            .where(
                AutopilotRunModel.created_at >= window.start,
                AutopilotRunModel.created_at < window.end,
                or_(
                    TopicCandidateModel.content_mode.is_(None),
                    TopicCandidateModel.content_mode == CONTENT_MODE_NEWS_ANALYSIS,
                ),
            )
        )
        return int(result.scalar_one())

    async def add_candidate(self, candidate: TopicCandidate) -> bool:
        """Insert one candidate. False when a concurrent batch stored its hash."""
        try:
            async with self._session.begin_nested():
                self._session.add(topic_row(candidate))
                await self._session.flush()
        except IntegrityError:
            return False
        return True

    async def lock_intake(self) -> None:
        """Transaction-scoped advisory lock on PostgreSQL; a no-op elsewhere.

        Two concurrent POSTs would otherwise both read "hash unknown" and
        "under the daily cap" before either commits (QA r1).
        """
        await advisory_xact_lock(self._session, INTAKE_LOCK_KEY)

    async def add_queued_run(self, command: QueuedRunCommand) -> None:
        """Insert a queued run stamped with the intake clock."""
        self._session.add(_run_row(command))
        await self._session.flush()

    async def commit(self) -> None:
        """Commit the current unit of work."""
        await self._session.commit()

    async def _upsert(self, url: str, served_at: datetime) -> None:
        existing = await self._session.get(ServedSignalUrlModel, url)
        if existing is None:
            self._session.add(ServedSignalUrlModel(url=url, served_at=served_at))
            return
        existing.served_at = served_at


def _canonical_urls(urls: tuple[str, ...]) -> tuple[str, ...]:
    ordered: dict[str, None] = {}
    for url in urls:
        canonical = canonical_url(url)
        if canonical != "":
            ordered[canonical] = None
    return tuple(ordered)


def _run_row(command: QueuedRunCommand) -> AutopilotRunModel:
    return AutopilotRunModel(
        id=command.run_id,
        carousel_project_id=None,
        topic_candidate_id=command.topic_candidate_id,
        state=AutopilotRunState.QUEUED.value,
        state_reason=None,
        publish_attempts=RUN_ATTEMPTS_INITIAL,
        start_attempts=RUN_ATTEMPTS_INITIAL,
        telegram_message_ids=[],
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
        created_at=command.created_at,
        updated_at=command.created_at,
    )
