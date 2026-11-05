"""Who the scan may notify, re-checked at the stage, on a real database.

Feature: backend/tests/features/scan_escalation_renotice_ae0618.feature
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.domain.carousel_retry import (
    carousel_retry_keyboard,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from tests.integration.pg_schema_support import requires_postgres
from tests.integration.scan_renotice_support import (
    BEFORE_RETRY,
    DEAD,
    REASON,
    RETRY_DEPLOYED,
    SCAN_DAY,
    SETTLED,
    STATE_CHANGED,
    FakeTelegram,
    assert_skipped,
    daily_scan,
    escalation_event,
    ledger,
    move_run,
    past_notice,
    renotice_markers,
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
PUBLISH_NOTICE = "content.autopilot.publish_notice"
FAILED_PUBLISH: dict[str, object] = {
    "outcome": "publish_failed",
    "error_code": "ig_error",
}
OPEN = {"phase_status": "awaiting_human", "status": "pending"}
PHASE_FAILED = {
    "current_phase": "outline",
    "phase_status": "failed",
    "status": "pending",
}
AUTO_REJECTED = {"phase_status": "rejected", "status": "failed"}
ARCHIVED = {**OPEN, "archived_at": BEFORE_RETRY}
PUBLISHED = {**OPEN, "current_phase": "published"}


async def assert_not_staged(engine: AsyncEngine, run_id: str, staged: bool) -> None:
    assert staged is False
    assert await renotices(engine, run_id) == []
    assert renotice_markers(await ledger(engine, run_id)) == []


@pytest.mark.parametrize("state", [_S.ESCALATED, _S.FAILED])
async def test_a_run_the_queue_parked_is_skipped(
    engine: AsyncEngine, state: _S
) -> None:
    """Scenario Outline: A run the queue parked is skipped"""
    await assert_skipped(engine, await stuck(engine, (state, DEAD)))


@pytest.mark.parametrize("state", ["escalated", "failed"])
async def test_a_run_parked_earlier_is_skipped(engine: AsyncEngine, state: str) -> None:
    """Scenario Outline: A run parked earlier is skipped whatever its reason is now"""
    run_id = await stuck(engine, (_S.ESCALATED, "phase_failed"))
    payload: dict[str, object] = {"state": state, "reason": DEAD}
    await past_notice(engine, run_id, (STATE_CHANGED, payload), BEFORE_RETRY)
    await assert_skipped(engine, run_id)


async def test_a_failed_publish_notice_that_offered_retry_counts(
    engine: AsyncEngine,
) -> None:
    """Scenario: A failed publish notice that offered Retry counts"""
    run_id = await stuck(engine, (_S.FAILED, "phase_failed"))
    await past_notice(engine, run_id, (PUBLISH_NOTICE, FAILED_PUBLISH), BEFORE_RETRY)
    await assert_skipped(engine, run_id)


async def test_a_failed_publish_notice_with_no_retry_does_not_count(
    engine: AsyncEngine,
) -> None:
    """Scenario: A failed publish notice with no Retry does not count"""
    run_id = await stuck(engine, (_S.FAILED, "phase_failed"))
    payload: dict[str, object] = {**FAILED_PUBLISH, "offer_retry": False}
    await past_notice(engine, run_id, (PUBLISH_NOTICE, payload), BEFORE_RETRY)
    report = await daily_scan(engine).run_once()
    assert report.renotified == 1
    assert len(await renotices(engine, run_id)) == 1


async def test_the_first_scan_picks_exactly_the_three_approved_runs(
    engine: AsyncEngine,
) -> None:
    """Scenario: The first scan after the deploy picks exactly the three approved runs"""
    persona = await stuck(engine, (_S.ESCALATED, REASON), OPEN)
    quality = await stuck(engine, (_S.ESCALATED, "content_quality"), OPEN)
    phase = await stuck(engine, (_S.ESCALATED, "phase_failed"), PHASE_FAILED)
    approved = {persona, quality, phase}
    for run_id in approved:
        await escalation_event(engine, run_id, BEFORE_RETRY)
    await tick(engine, FakeTelegram())
    skipped = {
        await stuck(engine, (_S.FAILED, "owner_queue_cancelled"), OPEN),
        await _autopilot_run(
            engine, _S.FAILED, "owner_queue_cancelled", timedelta(days=3)
        ),
        await stuck(engine, (_S.FAILED, "engine_error"), AUTO_REJECTED),
        await stuck(engine, (_S.FAILED, "engine_error"), AUTO_REJECTED),
        await stuck(engine, (_S.GENERATING, None), OPEN),
        await stuck(engine, (_S.ESCALATED, DEAD), OPEN),
        await stuck(engine, (_S.ESCALATED, "content_quality"), ARCHIVED),
        await stuck(engine, (_S.ESCALATED, "content_quality"), PUBLISHED),
    }

    assert set(await renotifier(engine).stuck_runs()) == approved
    report = await daily_scan(engine).run_once()
    assert report.renotified == 3
    assert report.renotify_failures == ()
    for run_id in skipped:
        assert await renotices(engine, run_id) == []
    telegram = FakeTelegram()
    assert await tick(engine, telegram) == 3
    assert {str(notice.run_id) for notice in telegram.sent} == approved
    for notice in telegram.sent:
        assert notice.keyboard == carousel_retry_keyboard(notice.run_id)
    assert (await daily_scan(engine).run_once()).renotified == 0


async def test_a_run_that_escalates_after_the_listing_gets_no_notice(
    engine: AsyncEngine,
) -> None:
    """Scenario Outline: A run that changed between the listing and the stage gets no notice"""
    run_id = await stuck(engine)
    port = renotifier(engine)
    assert await port.stuck_runs() == [run_id]
    await escalation_event(engine, run_id, SCAN_DAY)
    await assert_not_staged(engine, run_id, await port.renotify(run_id))


async def test_a_run_the_queue_parks_after_the_listing_gets_no_notice(
    engine: AsyncEngine,
) -> None:
    """Scenario Outline: A run that changed between the listing and the stage gets no notice"""
    run_id = await stuck(engine)
    port = renotifier(engine)
    assert await port.stuck_runs() == [run_id]
    await move_run(engine, run_id, state_reason=DEAD)
    await assert_not_staged(engine, run_id, await port.renotify(run_id))


@pytest.mark.parametrize(
    "values",
    [
        pytest.param({"state": "generating"}, id="owner retried"),
        pytest.param(
            {"state": "failed", "state_reason": "owner_queue_cancelled"},
            id="owner cancelled",
        ),
    ],
)
async def test_a_run_the_owner_acts_on_after_the_listing_gets_no_notice(
    engine: AsyncEngine, values: dict[str, object]
) -> None:
    """Scenario Outline: A run that changed between the listing and the stage gets no notice"""
    run_id = await stuck(engine)
    port = renotifier(engine)
    assert await port.stuck_runs() == [run_id]
    await move_run(engine, run_id, **values)
    await assert_not_staged(engine, run_id, await port.renotify(run_id))


@pytest.mark.parametrize("carousel", SETTLED)
async def test_a_carousel_that_changes_after_the_listing_stops_the_notice(
    engine: AsyncEngine, carousel: dict[str, object]
) -> None:
    """Scenario Outline: A run that changed between the listing and the stage gets no notice"""
    run_id = await stuck(engine)
    port = renotifier(engine)
    assert await port.stuck_runs() == [run_id]
    async with _sessions(engine)() as session:
        await session.execute(update(CarouselProjectModel).values(**carousel))
        await session.commit()
    await assert_not_staged(engine, run_id, await port.renotify(run_id))


async def test_an_eligible_run_still_stages_after_the_recheck(
    engine: AsyncEngine,
) -> None:
    """Scenario: An eligible escalated run gets one notice with the carousel Retry"""
    run_id = await stuck(engine)
    await escalation_event(engine, run_id, RETRY_DEPLOYED - timedelta(seconds=1))
    port = renotifier(engine)
    assert await port.stuck_runs() == [run_id]
    assert await port.renotify(run_id) is True
    assert len(await renotices(engine, run_id)) == 1


@requires_postgres
async def test_the_stage_waits_for_a_carousel_write_in_flight(
    engine: AsyncEngine,
) -> None:
    """Scenario: The stage waits for a carousel write in flight"""
    run_id = await stuck(engine)
    port = renotifier(engine)
    assert await port.stuck_runs() == [run_id]
    async with _sessions(engine)() as session:
        await session.execute(
            update(CarouselProjectModel).values(phase_status="rejected")
        )
        await session.flush()
        stage = asyncio.create_task(port.renotify(run_id))
        await asyncio.sleep(0.5)
        assert not stage.done()
        await session.commit()
    await assert_not_staged(engine, run_id, await stage)
