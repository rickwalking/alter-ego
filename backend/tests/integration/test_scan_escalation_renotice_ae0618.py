"""The daily scan's re-notify step and the notifier, on a real database.

Feature: backend/tests/features/scan_escalation_renotice_ae0618.feature
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import inspect, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.modules.autopilot.application.notifications import (
    NotificationDependencies,
    OwnerNotificationService,
)
from rag_backend.modules.autopilot.domain.carousel_retry import (
    carousel_retry_keyboard,
)
from rag_backend.modules.autopilot.domain.dead_letter import dead_letter_keyboard
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
from rag_backend.modules.autopilot.infrastructure import escalation_renotice
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
    summary_text,
)
from rag_backend.modules.generation_queue.domain.recovery import ScanReport
from rag_backend.modules.generation_queue.infrastructure.escalation_renotifier import (
    SqlEscalationRenotifier,
)
from rag_backend.modules.generation_queue.infrastructure.recovery_store import (
    SqlRecoveryStore,
)
from tests.integration.pg_schema_support import requires_postgres
from tests.integration.test_daily_recovery_scan_ae0524 import (
    _autopilot_run,
    _bridge,
    _sessions,
    engine,
)

__all__ = ["engine"]

_S = AutopilotRunState
_Columns = dict[str, object]
_REASON = "persona_score_below_threshold"
_RENOTICE = "content.autopilot.escalation_renotice"
_STATE_CHANGED = "content.autopilot.state_changed"
_MARKER = "scan_renotified"
_DEAD = "queue_dead_letter:run_budget_exhausted"
_SCAN_DAY = datetime(2026, 11, 5, 7, 0, tzinfo=UTC)
_BEFORE_RETRY = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
_RETRY_DEPLOYED = datetime(2026, 11, 4, 9, 21, 21, tzinfo=UTC)
_WAITING = {"phase_status": "awaiting_human"}
_SETTLED = [
    pytest.param({"phase_status": "rejected"}, id="rejected"),
    pytest.param({"phase_status": "approved"}, id="approved at its phase"),
    pytest.param(
        {"workflow_status": "approved_for_publish"}, id="approved for publish"
    ),
    pytest.param({"current_phase": "published"}, id="published"),
    pytest.param({"archived_at": _BEFORE_RETRY}, id="archived"),
    pytest.param({"phase_status": "in_progress"}, id="running"),
]


class _Clock:
    def now(self) -> datetime:
        return _SCAN_DAY


@dataclass
class _Telegram:
    failing: bool = False
    sent: list[StatusNotice] = field(default_factory=list)

    async def send_review(self, notice: ReviewNotice) -> ReviewSendResult:
        raise AssertionError(notice)

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        if self.failing:
            raise TelegramDeliveryError(detail="status 500")
        self.sent.append(notice)
        return StatusSendResult(message_id=len(self.sent))


class _NoFacts:
    async def load(self, project_id: str) -> ReviewFacts | None:
        del project_id
        return None


def _renotifier(engine: AsyncEngine) -> SqlEscalationRenotifier:
    sessions = _sessions(engine)
    return SqlEscalationRenotifier(AutopilotRenoticeBridge(sessions=sessions), sessions)


def _daily_scan(engine: AsyncEngine) -> DailyRecoveryScan:
    return DailyRecoveryScan(
        DailyScanDependencies(
            store=SqlRecoveryStore(_sessions(engine)),
            autopilot=_bridge(engine),
            renotifier=_renotifier(engine),
            clock=_Clock(),
        )
    )


async def _tick(engine: AsyncEngine, telegram: _Telegram) -> int:
    async with _sessions(engine)() as session:
        sent = await OwnerNotificationService(
            NotificationDependencies(
                events=SqlAutopilotEventSource(session),
                runs=SqlAlchemyAutopilotRepository(session),
                facts=_NoFacts(),
                notices=SqlNoticeLogStore(session),
                notifier=telegram,
                clock=_Clock(),
                chat_id="owner-chat",
                configured=True,
                web_base_url="https://example.com",
            )
        ).tick()
        await session.commit()
    return sent


async def _stuck(
    engine: AsyncEngine,
    run: tuple[_S, str | None] = (_S.ESCALATED, _REASON),
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


async def _escalation_event(
    engine: AsyncEngine, run_id: str, at: datetime, state: str = "escalated"
) -> None:
    async with _sessions(engine)() as session:
        session.add(
            EventOutboxModel(
                event_id=str(uuid4()),
                event_type=_STATE_CHANGED,
                aggregate_id=run_id,
                aggregate_type="autopilot_run",
                version=1,
                payload={"state": state, "reason": _REASON},
                metadata_json={},
                event_timestamp=at.isoformat(),
                created_at=at,
            )
        )
        await session.commit()


async def _renotices(engine: AsyncEngine, run_id: str) -> list[EventOutboxModel]:
    async with _sessions(engine)() as session:
        result = await session.execute(
            select(EventOutboxModel).where(
                EventOutboxModel.aggregate_id == run_id,
                EventOutboxModel.event_type == _RENOTICE,
            )
        )
        return list(result.scalars().all())


async def _ledger(engine: AsyncEngine, run_id: str) -> NoticeLog:
    async with _sessions(engine)() as session:
        row = await session.get(AutopilotRunModel, UUID(run_id))
    assert row is not None
    return parse_stored(row.telegram_message_ids)


async def _skipped(engine: AsyncEngine, run_id: str) -> None:
    report = await _daily_scan(engine).run_once()
    assert report.renotified == 0
    assert await _renotices(engine, run_id) == []
    assert _MARKER not in (await _ledger(engine, run_id)).statuses


async def test_an_eligible_escalated_run_gets_one_notice_with_the_retry(
    engine: AsyncEngine,
) -> None:
    """Scenario: An eligible escalated run gets one notice with the carousel Retry"""
    run_id = await _stuck(engine)
    report = await _daily_scan(engine).run_once()
    assert report.renotified == 1
    events = await _renotices(engine, run_id)
    assert len(events) == 1
    assert events[0].aggregate_type == "autopilot_run"
    assert events[0].payload == {"state": "escalated", "reason": _REASON}
    telegram = _Telegram()
    assert await _tick(engine, telegram) == 1
    assert len(telegram.sent) == 1
    notice = telegram.sent[0]
    assert notice.run_id == UUID(run_id)
    assert notice.keyboard == carousel_retry_keyboard(UUID(run_id))
    assert notice.text.startswith(f"Escalated: {_REASON}")
    assert await _tick(engine, telegram) == 0
    statuses = (await _ledger(engine, run_id)).statuses
    assert set(statuses) == {_MARKER, str(events[0].event_id)}


async def test_a_failed_run_with_a_live_carousel_gets_the_same_notice(
    engine: AsyncEngine,
) -> None:
    """Scenario: A failed run with a live carousel gets the same notice"""
    run_id = await _stuck(
        engine, (_S.FAILED, "phase_failed"), {"phase_status": "failed"}
    )
    await _daily_scan(engine).run_once()
    telegram = _Telegram()
    await _tick(engine, telegram)
    assert telegram.sent[0].keyboard == carousel_retry_keyboard(UUID(run_id))
    assert telegram.sent[0].text.startswith("Escalated: phase_failed")


async def test_a_second_scan_sends_nothing(engine: AsyncEngine) -> None:
    """Scenario: A second scan sends nothing"""
    run_id = await _stuck(engine)
    await _daily_scan(engine).run_once()
    telegram = _Telegram()
    await _tick(engine, telegram)
    report = await _daily_scan(engine).run_once()
    assert report.renotified == 0
    assert len(await _renotices(engine, run_id)) == 1
    await _tick(engine, telegram)
    assert len(telegram.sent) == 1


async def test_a_notice_still_in_the_outbox_is_not_emitted_again(
    engine: AsyncEngine,
) -> None:
    """Scenario: A notice still waiting in the outbox is not emitted again"""
    run_id = await _stuck(engine)
    await _daily_scan(engine).run_once()
    report = await _daily_scan(engine).run_once()
    assert report.renotified == 0
    assert len(await _renotices(engine, run_id)) == 1


async def test_a_notice_the_notifier_gave_up_on_is_not_offered_again(
    engine: AsyncEngine,
) -> None:
    """Scenario: A notice the notifier gave up on is not offered again"""
    run_id = await _stuck(engine)
    await _daily_scan(engine).run_once()
    for _ in range(3):
        await _tick(engine, _Telegram(failing=True))
    report = await _daily_scan(engine).run_once()
    assert report.renotified == 0
    assert len(await _renotices(engine, run_id)) == 1


@pytest.mark.parametrize("carousel", _SETTLED)
async def test_a_settled_or_running_carousel_is_skipped(
    engine: AsyncEngine, carousel: dict[str, object]
) -> None:
    """Scenario Outline: A settled or running carousel is skipped"""
    await _skipped(engine, await _stuck(engine, carousel=carousel))


async def test_a_failed_run_with_an_auto_rejected_carousel_is_skipped(
    engine: AsyncEngine,
) -> None:
    """Scenario: A failed run with an auto-rejected carousel is skipped"""
    run_id = await _stuck(
        engine,
        (_S.FAILED, "phase_failed"),
        {"phase_status": "rejected", "status": "failed"},
    )
    await _skipped(engine, run_id)


async def test_a_running_carousel_is_picked_up_once_it_stops(
    engine: AsyncEngine,
) -> None:
    """Scenario: A running carousel is picked up once it stops"""
    run_id = await _stuck(engine, carousel={"phase_status": "in_progress"})
    await _skipped(engine, run_id)
    async with _sessions(engine)() as session:
        await session.execute(update(CarouselProjectModel).values(**_WAITING))
        await session.commit()
    report = await _daily_scan(engine).run_once()
    assert report.renotified == 1
    assert len(await _renotices(engine, run_id)) == 1


async def test_a_run_already_notified_with_retry_is_skipped(
    engine: AsyncEngine,
) -> None:
    """Scenario: A run already notified with Retry is skipped"""
    run_id = await _stuck(engine)
    await _escalation_event(engine, run_id, _RETRY_DEPLOYED)
    await _tick(engine, _Telegram())
    await _skipped(engine, run_id)


async def test_an_escalation_not_delivered_yet_still_counts(
    engine: AsyncEngine,
) -> None:
    """Scenario: An escalation not delivered yet still counts as notified"""
    run_id = await _stuck(engine)
    await _escalation_event(engine, run_id, _SCAN_DAY - timedelta(minutes=1))
    await _skipped(engine, run_id)


async def test_an_escalation_before_retry_shipped_does_not_count(
    engine: AsyncEngine,
) -> None:
    """Scenario: An eligible escalated run gets one notice with the carousel Retry"""
    run_id = await _stuck(engine)
    moment = _RETRY_DEPLOYED - timedelta(seconds=1)
    await _escalation_event(engine, run_id, moment)
    report = await _daily_scan(engine).run_once()
    assert report.renotified == 1


async def test_a_later_notice_of_another_state_does_not_count(
    engine: AsyncEngine,
) -> None:
    """Scenario: A failed run with a live carousel gets the same notice"""
    run_id = await _stuck(engine, (_S.FAILED, "phase_failed"))
    await _escalation_event(engine, run_id, _SCAN_DAY, state="failed")
    report = await _daily_scan(engine).run_once()
    assert report.renotified == 1


async def test_another_runs_escalation_does_not_count(engine: AsyncEngine) -> None:
    """Scenario: An eligible escalated run gets one notice with the carousel Retry"""
    run_id = await _stuck(engine)
    other = await _stuck(engine)
    await _escalation_event(engine, other, _RETRY_DEPLOYED)
    report = await _daily_scan(engine).run_once()
    assert report.renotified == 1
    assert len(await _renotices(engine, run_id)) == 1
    assert await _renotices(engine, other) == []


@pytest.mark.parametrize(
    "reason",
    [
        "owner_queue_cancelled",
        "owner_queue_discard",
        "owner_queue_retry",
        "queue_daily_recovery",
    ],
)
async def test_a_run_closed_by_the_owner_or_a_retry_is_skipped(
    engine: AsyncEngine, reason: str
) -> None:
    """Scenario Outline: A run closed by the owner or by a retry is skipped"""
    await _skipped(engine, await _stuck(engine, (_S.FAILED, reason)))


async def test_a_run_with_no_carousel_is_skipped(engine: AsyncEngine) -> None:
    """Scenario: A run with no carousel is skipped"""
    run_id = await _autopilot_run(engine, _S.FAILED, "x", timedelta(days=3))
    await _skipped(engine, run_id)


async def test_a_run_in_any_other_state_is_skipped(engine: AsyncEngine) -> None:
    """Scenario: A run in any other state is skipped"""
    await _skipped(engine, await _stuck(engine, (_S.AWAITING_OWNER, None)))


async def test_a_run_the_queue_parked_keeps_its_own_buttons(
    engine: AsyncEngine,
) -> None:
    """Scenario: A run the queue parked keeps its own buttons"""
    run_id = await _stuck(engine, (_S.ESCALATED, _DEAD))
    await _daily_scan(engine).run_once()
    telegram = _Telegram()
    await _tick(engine, telegram)
    assert telegram.sent[0].keyboard == dead_letter_keyboard(UUID(run_id))


async def test_a_failed_item_writes_nothing_and_stays_eligible(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: A failed item writes nothing and stays eligible"""
    run_id = await _stuck(engine)
    original = escalation_renotice.SqlNoticeLogStore.save

    async def broken(self: SqlNoticeLogStore, command: object) -> None:
        del self, command
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(escalation_renotice.SqlNoticeLogStore, "save", broken)
    first = await _daily_scan(engine).run_once()
    assert first.renotified == 0
    assert [item.run_id for item in first.renotify_failures] == [run_id]
    assert await _renotices(engine, run_id) == []
    assert _MARKER not in (await _ledger(engine, run_id)).statuses
    monkeypatch.setattr(escalation_renotice.SqlNoticeLogStore, "save", original)
    second = await _daily_scan(engine).run_once()
    assert second.renotified == 1
    assert len(await _renotices(engine, run_id)) == 1


async def test_the_summary_carries_the_count(engine: AsyncEngine) -> None:
    """Scenario: The summary carries the count"""
    await _stuck(engine)
    await _stuck(engine, (_S.FAILED, "phase_failed"))
    report = await _daily_scan(engine).run_once()
    assert isinstance(report, ScanReport)
    assert "reenviado a 2 execução(ões)" in summary_text(report)


async def test_nothing_else_changes(engine: AsyncEngine) -> None:
    """Scenario: Nothing else changes"""

    def columns(row: AutopilotRunModel | CarouselProjectModel | None) -> _Columns:
        assert row is not None
        return {key: getattr(row, key) for key in inspect(row).mapper.columns.keys()}

    async def snapshot(run_id: str) -> tuple[_Columns, _Columns]:
        async with _sessions(engine)() as session:
            run = await session.get(AutopilotRunModel, UUID(run_id))
            assert run is not None
            carousel = await session.get(CarouselProjectModel, run.carousel_project_id)
            return columns(run), columns(carousel)

    run_id = await _stuck(engine)
    run_before, carousel_before = await snapshot(run_id)
    await _daily_scan(engine).run_once()
    await _tick(engine, _Telegram())
    run_after, carousel_after = await snapshot(run_id)
    assert carousel_after == carousel_before
    run_before.pop("telegram_message_ids")
    assert run_after.pop("telegram_message_ids") != []
    assert run_after == run_before


@requires_postgres
async def test_concurrent_scans_emit_one_event(engine: AsyncEngine) -> None:
    """Scenario: Concurrent scans emit one event"""
    run_id = await _stuck(engine)
    first, second = await asyncio.gather(
        _daily_scan(engine).run_once(), _daily_scan(engine).run_once()
    )
    assert first.renotified + second.renotified == 1
    assert len(await _renotices(engine, run_id)) == 1


async def test_a_run_that_moved_on_after_the_listing_is_left_alone(
    engine: AsyncEngine,
) -> None:
    """Scenario: A run that moved on after the listing is left alone"""
    run_id = await _stuck(engine)
    renotifier = _renotifier(engine)
    assert await renotifier.stuck_runs() == [run_id]
    async with _sessions(engine)() as session:
        await session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.id == UUID(run_id))
            .values(state=_S.GENERATING.value)
        )
        await session.commit()
    assert await renotifier.renotify(run_id) is False
    assert await _renotices(engine, run_id) == []


async def test_an_unknown_run_is_not_renotified(engine: AsyncEngine) -> None:
    """Scenario: A run that moved on after the listing is left alone"""
    assert await _renotifier(engine).renotify(str(uuid4())) is False


async def test_nothing_is_stuck_on_an_empty_table(engine: AsyncEngine) -> None:
    """Scenario: A quiet day's summary does not change"""
    assert await _renotifier(engine).stuck_runs() == []
