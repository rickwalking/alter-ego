"""A re-sent notice that never arrived gets another chance, and never two arrive.

Feature: backend/tests/features/scan_escalation_renotice_ae0618.feature
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.modules.autopilot.domain.carousel_retry import (
    carousel_retry_keyboard,
)
from rag_backend.modules.autopilot.domain.exceptions import TelegramRateLimitedError
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import NotifyCursorModel
from tests.integration.pg_schema_support import requires_postgres
from tests.integration.scan_renotice_support import (
    FakeTelegram,
    daily_scan,
    give_up,
    move_run,
    renotices,
    stuck,
    tick,
)
from tests.integration.test_daily_recovery_scan_ae0524 import _sessions, engine

__all__ = ["engine"]


async def test_a_given_up_notice_gets_another_chance_and_arrives_once(
    engine: AsyncEngine,
) -> None:
    """Scenario: A notice the notifier gave up on gets another chance on the next scan"""
    run_id = await stuck(engine)
    await daily_scan(engine).run_once()
    await give_up(engine)

    report = await daily_scan(engine).run_once()

    assert report.renotified == 1
    assert len(await renotices(engine, run_id)) == 2
    telegram = FakeTelegram()
    assert await tick(engine, telegram) == 1
    assert telegram.sent[0].keyboard == carousel_retry_keyboard(telegram.sent[0].run_id)
    assert (await daily_scan(engine).run_once()).renotified == 0
    assert await tick(engine, telegram) == 0
    assert len(telegram.sent) == 1
    assert len(await renotices(engine, run_id)) == 2


async def test_a_notice_that_keeps_failing_is_queued_once_per_scan(
    engine: AsyncEngine,
) -> None:
    """Scenario: A notice that keeps failing is queued once per scan"""
    run_id = await stuck(engine)
    await daily_scan(engine).run_once()
    await give_up(engine)
    await daily_scan(engine).run_once()
    assert (await daily_scan(engine).run_once()).renotified == 0
    await give_up(engine)
    assert (await daily_scan(engine).run_once()).renotified == 1
    assert len(await renotices(engine, run_id)) == 3


async def test_a_notice_still_being_retried_is_not_queued_again(
    engine: AsyncEngine,
) -> None:
    """Scenario: A notice still being retried is not queued again"""
    run_id = await stuck(engine)
    await daily_scan(engine).run_once()
    await tick(engine, FakeTelegram(failing=True))
    assert (await daily_scan(engine).run_once()).renotified == 0
    assert len(await renotices(engine, run_id)) == 1


async def test_a_run_that_moved_on_is_not_queued_again(engine: AsyncEngine) -> None:
    """Scenario: A run that moved on is not queued again after a give-up"""
    run_id = await stuck(engine)
    await daily_scan(engine).run_once()
    await give_up(engine)
    await move_run(engine, run_id, state=AutopilotRunState.GENERATING.value)
    assert (await daily_scan(engine).run_once()).renotified == 0
    assert len(await renotices(engine, run_id)) == 1


@requires_postgres
async def test_two_scans_after_a_give_up_queue_one_notice(engine: AsyncEngine) -> None:
    """Scenario: Two scans after a give-up queue one notice"""
    run_id = await stuck(engine)
    await daily_scan(engine).run_once()
    await give_up(engine)
    first, second = await asyncio.gather(
        daily_scan(engine).run_once(), daily_scan(engine).run_once()
    )
    assert first.renotified + second.renotified == 1
    assert len(await renotices(engine, run_id)) == 2


async def test_a_crash_after_the_send_never_sends_twice(engine: AsyncEngine) -> None:
    """Scenario: A crash after the send never sends the notice twice"""
    run_id = await stuck(engine)
    await daily_scan(engine).run_once()
    crashing = FakeTelegram(crash_after_send=True)
    with pytest.raises(RuntimeError):
        await tick(engine, crashing)
    assert len(crashing.sent) == 1

    later = FakeTelegram()
    assert await tick(engine, later) == 0
    assert (await daily_scan(engine).run_once()).renotified == 0
    assert await tick(engine, later) == 0
    assert later.sent == []
    assert len(await renotices(engine, run_id)) == 1


async def test_a_rate_limited_send_stays_open(engine: AsyncEngine) -> None:
    """Scenario: A rate limited send stays open"""
    await stuck(engine)
    await daily_scan(engine).run_once()
    await tick(engine, FakeTelegram(error=TelegramRateLimitedError("limited")))
    telegram = FakeTelegram()
    assert await tick(engine, telegram) == 1
    assert len(telegram.sent) == 1


async def test_an_outbox_replay_sends_nothing(engine: AsyncEngine) -> None:
    """Scenario: An outbox replay sends nothing"""
    await stuck(engine)
    await daily_scan(engine).run_once()
    await tick(engine, FakeTelegram())
    async with _sessions(engine)() as session:
        await session.execute(delete(NotifyCursorModel))
        await session.commit()
    telegram = FakeTelegram()
    assert await tick(engine, telegram) == 0
    assert telegram.sent == []
