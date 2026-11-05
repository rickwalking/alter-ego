"""Seeds, the scan and the notifier tick for the re-notify integration tests."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.modules.autopilot.application.notifications import (
    NotificationDependencies,
    OwnerNotificationService,
)
from rag_backend.modules.autopilot.domain.escalation_renotice import RenoticeClaims
from rag_backend.modules.autopilot.domain.exceptions import TelegramDeliveryError
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import NoticeLog, parse_stored
from rag_backend.modules.autopilot.domain.notify import (
    ReviewFacts,
    ReviewNotice,
    ReviewSendResult,
    StatusNotice,
    StatusSendResult,
)
from rag_backend.modules.autopilot.infrastructure.escalation_renotice import (
    SqlRenoticeClaims,
)
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.infrastructure.notice_source import (
    SqlAutopilotEventSource,
    SqlNoticeLogStore,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.renotice_bridge import AutopilotRenoticeBridge
from rag_backend.modules.generation_queue.application.recovery_scan import (
    DailyRecoveryScan,
    DailyScanDependencies,
)
from rag_backend.modules.generation_queue.infrastructure.escalation_renotifier import (
    SqlEscalationRenotifier,
)
from rag_backend.modules.generation_queue.infrastructure.recovery_store import (
    SqlRecoveryStore,
)
from tests.integration.test_daily_recovery_scan_ae0524 import (
    _autopilot_run,
    _bridge,
    _sessions,
)

_S = AutopilotRunState
REASON = "persona_score_below_threshold"
RENOTICE = "content.autopilot.escalation_renotice"
STATE_CHANGED = "content.autopilot.state_changed"
MARKER = "scan_renotified"
DEAD = "queue_dead_letter:run_budget_exhausted"
SCAN_DAY = datetime(2026, 11, 5, 7, 0, tzinfo=UTC)
BEFORE_RETRY = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
RETRY_DEPLOYED = datetime(2026, 11, 4, 9, 21, 21, tzinfo=UTC)
WAITING = {"phase_status": "awaiting_human"}
SETTLED = [
    pytest.param({"phase_status": "rejected"}, id="rejected"),
    pytest.param({"phase_status": "approved"}, id="approved at its phase"),
    pytest.param(
        {"workflow_status": "approved_for_publish"}, id="approved for publish"
    ),
    pytest.param({"current_phase": "published"}, id="published"),
    pytest.param({"archived_at": BEFORE_RETRY}, id="archived"),
    pytest.param({"phase_status": "in_progress"}, id="running"),
]


class _Clock:
    def now(self) -> datetime:
        return SCAN_DAY


@dataclass
class FakeTelegram:
    failing: bool = False
    crash_after_send: bool = False
    error: Exception | None = None
    during_send: Callable[[], Awaitable[None]] | None = None
    sent: list[StatusNotice] = field(default_factory=list)

    async def send_review(self, notice: ReviewNotice) -> ReviewSendResult:
        raise AssertionError(notice)

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        if self.during_send is not None:
            await self.during_send()
        if self.failing:
            raise TelegramDeliveryError(detail="status 500")
        if self.error is not None:
            raise self.error
        self.sent.append(notice)
        if self.crash_after_send:
            raise RuntimeError("worker died")
        return StatusSendResult(message_id=len(self.sent))


@dataclass(frozen=True, kw_only=True)
class ClaimHooks:
    """What else happens around a worker's claim, to stage a race."""

    before_take: Callable[[], Awaitable[None]] | None = None
    after_release: Exception | None = None


@dataclass(frozen=True, kw_only=True)
class _HookedClaims:
    claims: RenoticeClaims
    hooks: ClaimHooks

    async def take(self, run_id: UUID, event_id: str) -> bool:
        if self.hooks.before_take is not None:
            await self.hooks.before_take()
        return await self.claims.take(run_id, event_id)

    async def release(self, run_id: UUID, event_id: str) -> None:
        await self.claims.release(run_id, event_id)
        if self.hooks.after_release is not None:
            raise self.hooks.after_release


class _NoFacts:
    async def load(self, project_id: str) -> ReviewFacts | None:
        del project_id
        return None


def renotifier(engine: AsyncEngine) -> SqlEscalationRenotifier:
    sessions = _sessions(engine)
    return SqlEscalationRenotifier(AutopilotRenoticeBridge(sessions=sessions), sessions)


def daily_scan(engine: AsyncEngine) -> DailyRecoveryScan:
    return DailyRecoveryScan(
        DailyScanDependencies(
            store=SqlRecoveryStore(_sessions(engine)),
            autopilot=_bridge(engine),
            renotifier=renotifier(engine),
            clock=_Clock(),
        )
    )


async def tick(
    engine: AsyncEngine,
    telegram: FakeTelegram,
    hooks: ClaimHooks | None = None,
) -> int:
    async with _sessions(engine)() as session:
        sent = await OwnerNotificationService(
            NotificationDependencies(
                events=SqlAutopilotEventSource(session),
                runs=SqlAlchemyAutopilotRepository(session),
                facts=_NoFacts(),
                notices=SqlNoticeLogStore(session),
                notifier=telegram,
                claims=_HookedClaims(
                    claims=SqlRenoticeClaims(session), hooks=hooks or ClaimHooks()
                ),
                clock=_Clock(),
                chat_id="owner-chat",
                configured=True,
                web_base_url="https://example.com",
            )
        ).tick()
        await session.commit()
    return sent


async def stuck(
    engine: AsyncEngine,
    run: tuple[_S, str | None] = (_S.ESCALATED, REASON),
    carousel: dict[str, object] | None = None,
) -> str:
    """A run from before Retry shipped, with its carousel."""
    run_id = await _autopilot_run(engine, run[0], run[1], timedelta(days=3))
    project_id = str(uuid4())
    columns: dict[str, object] = {
        "current_phase": "content",
        "phase_status": "awaiting_human",
        **(carousel or {}),
    }
    async with _sessions(engine)() as session:
        session.add(
            CarouselProjectModel(
                id=project_id, topic="t", audience="a", niche="n", **columns
            )
        )
        await session.flush()
        await session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.id == UUID(run_id))
            .values(carousel_project_id=project_id)
        )
        await session.commit()
    return run_id


async def past_notice(
    engine: AsyncEngine,
    run_id: str,
    event: tuple[str, dict[str, object]],
    at: datetime,
) -> None:
    async with _sessions(engine)() as session:
        session.add(
            EventOutboxModel(
                event_id=str(uuid4()),
                event_type=event[0],
                aggregate_id=run_id,
                aggregate_type="autopilot_run",
                version=1,
                payload=event[1],
                metadata_json={},
                event_timestamp=at.isoformat(),
                created_at=at,
            )
        )
        await session.commit()


async def escalation_event(
    engine: AsyncEngine, run_id: str, at: datetime, state: str = "escalated"
) -> None:
    payload: dict[str, object] = {"state": state, "reason": REASON}
    await past_notice(engine, run_id, (STATE_CHANGED, payload), at)


async def move_run(engine: AsyncEngine, run_id: str, **values: object) -> None:
    async with _sessions(engine)() as session:
        await session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.id == UUID(run_id))
            .values(**values)
        )
        await session.commit()


async def renotices(engine: AsyncEngine, run_id: str) -> list[EventOutboxModel]:
    async with _sessions(engine)() as session:
        result = await session.execute(
            select(EventOutboxModel).where(
                EventOutboxModel.aggregate_id == run_id,
                EventOutboxModel.event_type == RENOTICE,
            )
        )
        return list(result.scalars().all())


async def ledger(engine: AsyncEngine, run_id: str) -> NoticeLog:
    async with _sessions(engine)() as session:
        row = await session.get(AutopilotRunModel, UUID(run_id))
    assert row is not None
    return parse_stored(row.telegram_message_ids)


def renotice_markers(log: NoticeLog) -> list[str]:
    return [status for status in log.statuses if status.startswith(f"{MARKER}:")]


async def give_up(engine: AsyncEngine) -> None:
    """Every delivery attempt of the pending notices fails."""
    for _ in range(3):
        await tick(engine, FakeTelegram(failing=True))


async def assert_skipped(engine: AsyncEngine, run_id: str) -> None:
    report = await daily_scan(engine).run_once()
    assert report.renotified == 0
    assert await renotices(engine, run_id) == []
    assert renotice_markers(await ledger(engine, run_id)) == []
