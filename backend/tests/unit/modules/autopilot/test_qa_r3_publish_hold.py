"""A run held by a dead worker's container is resolved (QA r3 Q2).

A stale claim is never taken over blindly while a fresh container has no
post id. The job reads the container status once instead and acts on it.

Gherkin: tests/features/autopilot_instagram_publish.feature
  Scenario: A run held by a dead worker's container is resolved by its status
  Scenario: The owner is told once when a publish is held for 30 minutes
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.domain.constants.instagram_publish import (
    CONTAINER_STATUS_ERROR,
    CONTAINER_STATUS_EXPIRED,
    CONTAINER_STATUS_FINISHED,
    CONTAINER_STATUS_IN_PROGRESS,
    CONTAINER_STATUS_PUBLISHED,
    ERR_INSTAGRAM_CONTAINER_FAILED,
)
from rag_backend.modules.autopilot.application.publish_job import InstagramPublishJob
from rag_backend.modules.autopilot.domain.exceptions import InstagramCallError
from rag_backend.modules.autopilot.domain.messages import (
    StatusCopy,
    notice_kind,
    status_text,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.publish import PublishNotice, StoredContainer
from rag_backend.modules.autopilot.domain.publish_claims import RunClaim
from rag_backend.modules.autopilot.infrastructure.publish_notifier import _record
from rag_backend.modules.autopilot.notify_constants import KIND_PUBLISH_HELD
from rag_backend.modules.autopilot.recovery_constants import (
    MANUAL_CLAIM_STALE_MINUTES,
    NOTICE_PUBLISH_HELD,
    PUBLISH_HELD_NOTICE_MINUTES,
    REASON_PUBLISH_HELD,
)
from tests.unit.modules.autopilot.test_instagram_publish_job import (
    _Claims,
    _Clock,
    _deps,
    _Gateway,
    _Notifier,
    _Repo,
    _run,
    _snapshot,
    _Source,
    _store,
)


@dataclass
class _HeldClaims(_Claims):
    """``claim_run`` refuses held runs, like a stale claim over a fresh container."""

    stuck: set[UUID] = field(default_factory=set)
    live: bool = False
    takeovers: list[RunClaim] = field(default_factory=list)

    async def claim_run(self, claim: RunClaim) -> bool:
        if claim.run_id in self.stuck:
            return False
        return await super().claim_run(claim)

    async def take_over_held(self, claim: RunClaim) -> bool:
        self.takeovers.append(claim)
        if self.live:
            return False
        self.held.add(claim.run_id)
        return True


class _StatusGateway(_Gateway):
    def __init__(self, status: str) -> None:
        super().__init__()
        self.status = status
        self.status_reads: list[str] = []
        self.status_error = False

    async def container_status(self, container: StoredContainer) -> str:
        self.status_reads.append(container.container_id)
        if self.status_error:
            raise InstagramCallError(status_code=0, error_code="x", transient=True)
        return self.status


def _held(repo: _Repo, clock: _Clock, age: timedelta) -> AutopilotRun:
    return _store(
        repo,
        replace(
            _run(),
            ig_container_id="held-container",
            ig_container_created_at=clock.now() - age,
        ),
    )


def _setup(
    status: str, age: timedelta = timedelta(minutes=5)
) -> tuple[_Repo, _StatusGateway, _HeldClaims, _Notifier, AutopilotRun, _Clock]:
    repo, clock, notifier = _Repo(), _Clock(), _Notifier()
    gateway = _StatusGateway(status)
    run = _held(repo, clock, age)
    claims = _HeldClaims(stuck={run.run_id})
    return repo, gateway, claims, notifier, run, clock


def _job(
    repo: _Repo,
    gateway: _StatusGateway,
    claims: _HeldClaims,
    notifier: _Notifier,
    clock: _Clock,
) -> InstagramPublishJob:
    return InstagramPublishJob(
        _deps(repo, gateway, _Source(_snapshot()), clock, notifier, claims)
    )


# Scenario: A run held by a dead worker's container is resolved by its status
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status", [CONTAINER_STATUS_PUBLISHED, CONTAINER_STATUS_FINISHED]
)
async def test_a_published_or_finished_container_is_finished_under_the_claim(
    status: str,
) -> None:
    repo, gateway, claims, notifier, run, clock = _setup(status)

    assert await _job(repo, gateway, claims, notifier, clock).tick() == 1

    assert gateway.status_reads == ["held-container"]
    assert gateway.finishes == 1
    assert gateway.last_container == "held-container"
    assert gateway.opens == 0
    assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISHED
    stale = clock.now() - timedelta(minutes=MANUAL_CLAIM_STALE_MINUTES)
    assert [c.stale_before for c in claims.takeovers] == [stale]
    assert claims.released == [run.run_id]


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [CONTAINER_STATUS_ERROR, CONTAINER_STATUS_EXPIRED])
async def test_an_error_or_expired_container_fails_the_run(status: str) -> None:
    repo, gateway, claims, notifier, run, clock = _setup(status)

    assert await _job(repo, gateway, claims, notifier, clock).tick() == 1

    stored = repo.runs[run.run_id]
    assert stored.state is AutopilotRunState.PUBLISH_FAILED
    assert stored.state_reason == ERR_INSTAGRAM_CONTAINER_FAILED
    assert gateway.finishes == 0
    assert gateway.opens == 0
    assert [n.error_code for n in notifier.notices] == [ERR_INSTAGRAM_CONTAINER_FAILED]
    assert claims.released == [run.run_id]


@pytest.mark.asyncio
async def test_an_in_progress_container_keeps_waiting_silently() -> None:
    repo, gateway, claims, notifier, run, clock = _setup(CONTAINER_STATUS_IN_PROGRESS)

    assert await _job(repo, gateway, claims, notifier, clock).tick() == 0

    assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISHING
    assert gateway.finishes == 0
    assert claims.takeovers == []
    assert notifier.notices == []


@pytest.mark.asyncio
async def test_a_status_read_failure_keeps_waiting() -> None:
    repo, gateway, claims, notifier, run, clock = _setup(CONTAINER_STATUS_FINISHED)
    gateway.status_error = True

    assert await _job(repo, gateway, claims, notifier, clock).tick() == 0

    assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISHING
    assert claims.takeovers == []


@pytest.mark.asyncio
async def test_a_live_holder_keeps_the_run_even_when_the_container_is_finished() -> (
    None
):
    repo, gateway, claims, notifier, run, clock = _setup(CONTAINER_STATUS_FINISHED)
    claims.live = True

    assert await _job(repo, gateway, claims, notifier, clock).tick() == 0

    assert gateway.finishes == 0
    assert repo.runs[run.run_id].state is AutopilotRunState.PUBLISHING


@pytest.mark.asyncio
async def test_a_run_without_a_stored_container_is_not_probed() -> None:
    repo, clock, notifier = _Repo(), _Clock(), _Notifier()
    gateway = _StatusGateway(CONTAINER_STATUS_FINISHED)
    run = _store(repo, _run())
    claims = _HeldClaims(stuck={run.run_id})

    assert await _job(repo, gateway, claims, notifier, clock).tick() == 0

    assert gateway.status_reads == []
    assert claims.takeovers == []


# Scenario: The owner is told once when a publish is held for 30 minutes
@pytest.mark.asyncio
async def test_a_hold_longer_than_30_minutes_is_reported_once() -> None:
    age = timedelta(minutes=PUBLISH_HELD_NOTICE_MINUTES + 1)
    repo, gateway, claims, notifier, run, clock = _setup(
        CONTAINER_STATUS_IN_PROGRESS, age
    )
    job = _job(repo, gateway, claims, notifier, clock)

    await job.tick()
    await job.tick()

    assert [n.outcome for n in notifier.notices] == [NOTICE_PUBLISH_HELD]
    stored = repo.runs[run.run_id]
    assert stored.state is AutopilotRunState.PUBLISHING
    assert stored.state_reason == REASON_PUBLISH_HELD
    assert stored.publish_attempts == run.publish_attempts


@pytest.mark.asyncio
async def test_a_hold_under_30_minutes_is_not_reported() -> None:
    age = timedelta(minutes=PUBLISH_HELD_NOTICE_MINUTES - 1)
    repo, gateway, claims, notifier, _, clock = _setup(
        CONTAINER_STATUS_IN_PROGRESS, age
    )

    await _job(repo, gateway, claims, notifier, clock).tick()

    assert notifier.notices == []


def test_the_held_notice_renders_as_its_own_telegram_kind() -> None:
    notice = PublishNotice(
        run_id=uuid4(),
        outcome=NOTICE_PUBLISH_HELD,
        permalink=None,
        error_code=REASON_PUBLISH_HELD,
        offer_retry=False,
    )
    record = _record(notice)
    copy = StatusCopy(reason="", link="", permalink="", days_remaining=None)

    kind = notice_kind(record.event_type, record.payload)

    assert kind == KIND_PUBLISH_HELD
    assert str(PUBLISH_HELD_NOTICE_MINUTES) in status_text(kind, copy)
