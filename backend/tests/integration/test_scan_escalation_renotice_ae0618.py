"""The daily scan's re-notify step and the notifier, on a real database.

Feature: backend/tests/features/scan_escalation_renotice_ae0618.feature
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import inspect, update
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.domain.carousel_retry import (
    carousel_retry_keyboard,
)
from rag_backend.modules.autopilot.domain.dead_letter import dead_letter_keyboard
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure import escalation_renotice
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.autopilot.infrastructure.notice_source import SqlNoticeLogStore
from rag_backend.modules.generation_queue.application.recovery_scan import summary_text
from rag_backend.modules.generation_queue.domain.recovery import ScanReport
from tests.integration.pg_schema_support import requires_postgres
from tests.integration.scan_renotice_support import (
    DEAD,
    MARKER,
    REASON,
    RETRY_DEPLOYED,
    SCAN_DAY,
    SETTLED,
    WAITING,
    FakeTelegram,
    assert_skipped,
    daily_scan,
    escalation_event,
    ledger,
    renotices,
    renotifier,
    stuck,
    tick,
)
from tests.integration.test_daily_recovery_scan_ae0524 import (
    _autopilot_run,
    _sessions,
    engine,
)

__all__ = ["engine"]

_S = AutopilotRunState
_Columns = dict[str, object]


async def test_an_eligible_escalated_run_gets_one_notice_with_the_retry(
    engine: AsyncEngine,
) -> None:
    """Scenario: An eligible escalated run gets one notice with the carousel Retry"""
    run_id = await stuck(engine)
    report = await daily_scan(engine).run_once()
    assert report.renotified == 1
    events = await renotices(engine, run_id)
    assert len(events) == 1
    assert events[0].aggregate_type == "autopilot_run"
    assert events[0].payload == {"state": "escalated", "reason": REASON}
    telegram = FakeTelegram()
    assert await tick(engine, telegram) == 1
    assert len(telegram.sent) == 1
    notice = telegram.sent[0]
    assert notice.run_id == UUID(run_id)
    assert notice.keyboard == carousel_retry_keyboard(UUID(run_id))
    assert notice.text.startswith(f"Escalated: {REASON}")
    assert await tick(engine, telegram) == 0
    statuses = (await ledger(engine, run_id)).statuses
    assert set(statuses) == {MARKER, str(events[0].event_id)}


async def test_a_failed_run_with_a_live_carousel_gets_the_same_notice(
    engine: AsyncEngine,
) -> None:
    """Scenario: A failed run with a live carousel gets the same notice"""
    run_id = await stuck(
        engine, (_S.FAILED, "phase_failed"), {"phase_status": "failed"}
    )
    await daily_scan(engine).run_once()
    telegram = FakeTelegram()
    await tick(engine, telegram)
    assert telegram.sent[0].keyboard == carousel_retry_keyboard(UUID(run_id))
    assert telegram.sent[0].text.startswith("Escalated: phase_failed")


async def test_a_second_scan_sends_nothing(engine: AsyncEngine) -> None:
    """Scenario: A second scan sends nothing"""
    run_id = await stuck(engine)
    await daily_scan(engine).run_once()
    telegram = FakeTelegram()
    await tick(engine, telegram)
    report = await daily_scan(engine).run_once()
    assert report.renotified == 0
    assert len(await renotices(engine, run_id)) == 1
    await tick(engine, telegram)
    assert len(telegram.sent) == 1


async def test_a_notice_still_in_the_outbox_is_not_emitted_again(
    engine: AsyncEngine,
) -> None:
    """Scenario: A notice still waiting in the outbox is not emitted again"""
    run_id = await stuck(engine)
    await daily_scan(engine).run_once()
    report = await daily_scan(engine).run_once()
    assert report.renotified == 0
    assert len(await renotices(engine, run_id)) == 1


async def test_a_notice_the_notifier_gave_up_on_is_not_offered_again(
    engine: AsyncEngine,
) -> None:
    """Scenario: A notice the notifier gave up on is not offered again"""
    run_id = await stuck(engine)
    await daily_scan(engine).run_once()
    for _ in range(3):
        await tick(engine, FakeTelegram(failing=True))
    report = await daily_scan(engine).run_once()
    assert report.renotified == 0
    assert len(await renotices(engine, run_id)) == 1


@pytest.mark.parametrize("carousel", SETTLED)
async def test_a_settled_or_running_carousel_is_skipped(
    engine: AsyncEngine, carousel: dict[str, object]
) -> None:
    """Scenario Outline: A settled or running carousel is skipped"""
    await assert_skipped(engine, await stuck(engine, carousel=carousel))


async def test_a_failed_run_with_an_auto_rejected_carousel_is_skipped(
    engine: AsyncEngine,
) -> None:
    """Scenario: A failed run with an auto-rejected carousel is skipped"""
    run_id = await stuck(
        engine,
        (_S.FAILED, "phase_failed"),
        {"phase_status": "rejected", "status": "failed"},
    )
    await assert_skipped(engine, run_id)


async def test_a_running_carousel_is_picked_up_once_it_stops(
    engine: AsyncEngine,
) -> None:
    """Scenario: A running carousel is picked up once it stops"""
    run_id = await stuck(engine, carousel={"phase_status": "in_progress"})
    await assert_skipped(engine, run_id)
    async with _sessions(engine)() as session:
        await session.execute(update(CarouselProjectModel).values(**WAITING))
        await session.commit()
    report = await daily_scan(engine).run_once()
    assert report.renotified == 1
    assert len(await renotices(engine, run_id)) == 1


async def test_a_run_already_notified_with_retry_is_skipped(
    engine: AsyncEngine,
) -> None:
    """Scenario: A run already notified with Retry is skipped"""
    run_id = await stuck(engine)
    await escalation_event(engine, run_id, RETRY_DEPLOYED)
    await tick(engine, FakeTelegram())
    await assert_skipped(engine, run_id)


async def test_an_escalation_not_delivered_yet_still_counts(
    engine: AsyncEngine,
) -> None:
    """Scenario: An escalation not delivered yet still counts as notified"""
    run_id = await stuck(engine)
    await escalation_event(engine, run_id, SCAN_DAY - timedelta(minutes=1))
    await assert_skipped(engine, run_id)


async def test_an_escalation_before_retry_shipped_does_not_count(
    engine: AsyncEngine,
) -> None:
    """Scenario: An eligible escalated run gets one notice with the carousel Retry"""
    run_id = await stuck(engine)
    moment = RETRY_DEPLOYED - timedelta(seconds=1)
    await escalation_event(engine, run_id, moment)
    report = await daily_scan(engine).run_once()
    assert report.renotified == 1


async def test_a_later_notice_of_another_state_does_not_count(
    engine: AsyncEngine,
) -> None:
    """Scenario: A failed run with a live carousel gets the same notice"""
    run_id = await stuck(engine, (_S.FAILED, "phase_failed"))
    await escalation_event(engine, run_id, SCAN_DAY, state="failed")
    report = await daily_scan(engine).run_once()
    assert report.renotified == 1


async def test_another_runs_escalation_does_not_count(engine: AsyncEngine) -> None:
    """Scenario: An eligible escalated run gets one notice with the carousel Retry"""
    run_id = await stuck(engine)
    other = await stuck(engine)
    await escalation_event(engine, other, RETRY_DEPLOYED)
    report = await daily_scan(engine).run_once()
    assert report.renotified == 1
    assert len(await renotices(engine, run_id)) == 1
    assert await renotices(engine, other) == []


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
    await assert_skipped(engine, await stuck(engine, (_S.FAILED, reason)))


async def test_a_run_with_no_carousel_is_skipped(engine: AsyncEngine) -> None:
    """Scenario: A run with no carousel is skipped"""
    run_id = await _autopilot_run(engine, _S.FAILED, "x", timedelta(days=3))
    await assert_skipped(engine, run_id)


async def test_a_run_in_any_other_state_is_skipped(engine: AsyncEngine) -> None:
    """Scenario: A run in any other state is skipped"""
    await assert_skipped(engine, await stuck(engine, (_S.AWAITING_OWNER, None)))


async def test_a_run_the_queue_parked_keeps_its_own_buttons(
    engine: AsyncEngine,
) -> None:
    """Scenario: A run the queue parked keeps its own buttons"""
    run_id = await stuck(engine, (_S.ESCALATED, DEAD))
    await daily_scan(engine).run_once()
    telegram = FakeTelegram()
    await tick(engine, telegram)
    assert telegram.sent[0].keyboard == dead_letter_keyboard(UUID(run_id))


async def test_a_failed_item_writes_nothing_and_stays_eligible(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: A failed item writes nothing and stays eligible"""
    run_id = await stuck(engine)
    original = escalation_renotice.SqlNoticeLogStore.save

    async def broken(self: SqlNoticeLogStore, command: object) -> None:
        del self, command
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(escalation_renotice.SqlNoticeLogStore, "save", broken)
    first = await daily_scan(engine).run_once()
    assert first.renotified == 0
    assert [item.run_id for item in first.renotify_failures] == [run_id]
    assert await renotices(engine, run_id) == []
    assert MARKER not in (await ledger(engine, run_id)).statuses
    monkeypatch.setattr(escalation_renotice.SqlNoticeLogStore, "save", original)
    second = await daily_scan(engine).run_once()
    assert second.renotified == 1
    assert len(await renotices(engine, run_id)) == 1


async def test_the_summary_carries_the_count(engine: AsyncEngine) -> None:
    """Scenario: The summary carries the count"""
    await stuck(engine)
    await stuck(engine, (_S.FAILED, "phase_failed"))
    report = await daily_scan(engine).run_once()
    assert isinstance(report, ScanReport)
    assert "reenviado a 2 execução(ões)" in summary_text(report)


async def test_nothing_else_changes(engine: AsyncEngine) -> None:
    """Scenario: Nothing else changes"""

    def columns(row: AutopilotRunModel | CarouselProjectModel | None) -> _Columns:
        assert row is not None
        attrs = inspect(row).mapper.column_attrs
        return {attr.key: getattr(row, attr.key) for attr in attrs}

    async def snapshot(run_id: str) -> tuple[_Columns, _Columns]:
        async with _sessions(engine)() as session:
            run = await session.get(AutopilotRunModel, UUID(run_id))
            assert run is not None
            carousel = await session.get(CarouselProjectModel, run.carousel_project_id)
            return columns(run), columns(carousel)

    run_id = await stuck(engine)
    run_before, carousel_before = await snapshot(run_id)
    await daily_scan(engine).run_once()
    await tick(engine, FakeTelegram())
    run_after, carousel_after = await snapshot(run_id)
    assert carousel_after == carousel_before
    run_before.pop("telegram_message_ids")
    assert run_after.pop("telegram_message_ids") != []
    assert run_after == run_before


@requires_postgres
async def test_concurrent_scans_emit_one_event(engine: AsyncEngine) -> None:
    """Scenario: Concurrent scans emit one event"""
    run_id = await stuck(engine)
    first, second = await asyncio.gather(
        daily_scan(engine).run_once(), daily_scan(engine).run_once()
    )
    assert first.renotified + second.renotified == 1
    assert len(await renotices(engine, run_id)) == 1


async def test_a_run_that_moved_on_after_the_listing_is_left_alone(
    engine: AsyncEngine,
) -> None:
    """Scenario: A run that moved on after the listing is left alone"""
    run_id = await stuck(engine)
    port = renotifier(engine)
    assert await port.stuck_runs() == [run_id]
    async with _sessions(engine)() as session:
        await session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.id == UUID(run_id))
            .values(state=_S.GENERATING.value)
        )
        await session.commit()
    assert await port.renotify(run_id) is False
    assert await renotices(engine, run_id) == []


async def test_an_unknown_run_is_not_renotified(engine: AsyncEngine) -> None:
    """Scenario: A run that moved on after the listing is left alone"""
    assert await renotifier(engine).renotify(str(uuid4())) is False


async def test_nothing_is_stuck_on_an_empty_table(engine: AsyncEngine) -> None:
    """Scenario: A quiet day's summary does not change"""
    assert await renotifier(engine).stuck_runs() == []
