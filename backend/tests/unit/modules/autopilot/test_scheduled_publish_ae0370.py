"""The worker's due tick for scheduled runs (AE-0370).

Gherkin: tests/features/autopilot_scheduled_publish.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

import pytest

from rag_backend.modules.autopilot.application.publish_job import InstagramPublishJob
from rag_backend.modules.autopilot.application.run_recovery import (
    RecoveryDependencies,
    RunRecovery,
)
from rag_backend.modules.autopilot.application.scheduled_publish import (
    ScheduledPublishDependencies,
    ScheduledPublishSweep,
)
from rag_backend.modules.autopilot.constants import (
    NOTICE_PUBLISH_FAILED,
    NOTICE_PUBLISHED,
)
from rag_backend.modules.autopilot.domain.gate import OwnerReadyNotice
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
)
from rag_backend.modules.autopilot.domain.owner_ports import ReleaseCommand
from rag_backend.modules.autopilot.domain.publish import PostExtras
from rag_backend.modules.autopilot.domain.published_copy import published_text
from rag_backend.modules.autopilot.domain.schedule_ports import DueScheduleQuery
from rag_backend.modules.autopilot.recovery_constants import REASON_OWNER_EXPIRED
from rag_backend.modules.autopilot.schedule_constants import (
    REASON_SCHEDULE_DUE,
    REASON_SCHEDULE_RELEASE_FAILED,
    REASON_SCHEDULE_WITHDRAWN,
)
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_instagram_publish_job import (
    _NOW,
    _PROJECT,
    _Clock,
    _deps,
    _Gateway,
    _Notifier,
    _Repo,
    _run,
    _snapshot,
    _Source,
)
from tests.unit.modules.autopilot.test_owner_actions import _Editorial

_S = AutopilotRunState
_DUE = _NOW + timedelta(hours=3)


@dataclass
class _Scheduled:
    repo: _Repo
    # True: another caller moves every listed run before the sweep's CAS.
    raced: bool = False

    async def due(self, query: DueScheduleQuery) -> list[AutopilotRun]:
        due = self._due(query)
        if self.raced:
            for run in due:
                self.repo.runs[run.run_id] = replace(run, state=_S.AWAITING_OWNER)
        return due

    def _due(self, query: DueScheduleQuery) -> list[AutopilotRun]:
        due = [
            run
            for run in self.repo.runs.values()
            if run.state is _S.SCHEDULED
            and run.scheduled_at is not None
            and run.scheduled_at <= query.now
        ]
        return sorted(due, key=lambda run: run.scheduled_at or query.now)[: query.limit]


@dataclass
class _Release:
    ok: bool = True
    ids: list[str] = field(default_factory=list)

    async def release(self, command: ReleaseCommand) -> bool:
        self.ids.append(command.project_id)
        return self.ok


@dataclass
class _Story:
    calls: list[str] = field(default_factory=list)

    async def run(self, project_id: str) -> PostExtras:
        self.calls.append(project_id)
        return PostExtras(
            story_status="published", story_error=None, music_style="lo-fi beats"
        )


@dataclass
class _Tick:
    repo: _Repo
    scheduled: _Scheduled
    clock: _Clock
    source: _Source
    release: _Release
    notifier: _Notifier
    gateway: _Gateway
    story: _Story
    sweep: ScheduledPublishSweep
    job: InstagramPublishJob

    @property
    def run(self) -> AutopilotRun:
        return next(iter(self.repo.runs.values()))

    async def worker(self) -> int:
        """The adapter's order: due sweep, then the publish job."""
        return await self.sweep.tick() + await self.job.tick()


def _scheduled_run(at: datetime = _DUE) -> AutopilotRun:
    return replace(_run(), state=_S.SCHEDULED, scheduled_at=at)


def _tick(run: AutopilotRun | None = None) -> _Tick:
    repo = _Repo()
    stored = run or _scheduled_run()
    repo.runs[stored.run_id] = stored
    clock = _Clock()
    source = _Source(_snapshot())
    release = _Release()
    notifier = _Notifier()
    gateway = _Gateway()
    story = _Story()
    scheduled = _Scheduled(repo)
    sweep = ScheduledPublishSweep(
        ScheduledPublishDependencies(
            runs=repo,
            scheduled=scheduled,
            source=source,
            release=release,
            notifier=notifier,
            checkpoint=repo,
            clock=clock,
        )
    )
    job = InstagramPublishJob(
        replace(_deps(repo, gateway, source, clock, notifier), story=story)
    )
    return _Tick(
        repo=repo,
        scheduled=scheduled,
        clock=clock,
        source=source,
        release=release,
        notifier=notifier,
        gateway=gateway,
        story=story,
        sweep=sweep,
        job=job,
    )


def _at(tick: _Tick, moment: datetime) -> None:
    tick.clock.current = moment


# Scenario: A due run publishes at its time
@pytest.mark.asyncio
async def test_not_due_publishes_nothing() -> None:
    tick = _tick()
    _at(tick, _DUE - timedelta(minutes=1))
    assert await tick.worker() == 0
    assert tick.run.state is _S.SCHEDULED
    assert tick.release.ids == []
    assert tick.gateway.opens == 0


@pytest.mark.asyncio
async def test_due_run_publishes_with_story_and_no_delay_line() -> None:
    tick = _tick()
    _at(tick, _DUE)
    assert await tick.sweep.tick() == 1
    assert tick.run.state is _S.PUBLISHING
    assert tick.run.state_reason == REASON_SCHEDULE_DUE
    assert tick.release.ids == [_PROJECT]
    assert tick.repo.commits == 1
    assert await tick.job.tick() == 1
    assert tick.run.state is _S.PUBLISHED
    assert tick.gateway.opens == 1
    assert tick.story.calls == [_PROJECT]
    notice = tick.notifier.notices[-1]
    assert notice.outcome == NOTICE_PUBLISHED
    assert notice.extras is not None
    assert notice.extras.late_minutes is None
    assert "atraso" not in published_text(notice.permalink or "", notice.extras)


@pytest.mark.asyncio
async def test_ten_minutes_late_is_on_time() -> None:
    tick = _tick()
    _at(tick, _DUE + timedelta(minutes=10))
    await tick.worker()
    extras = tick.notifier.notices[-1].extras
    assert extras is not None
    assert extras.late_minutes is None


# Scenario: A late run publishes anyway and says how late
@pytest.mark.asyncio
async def test_late_run_publishes_and_says_how_late() -> None:
    tick = _tick()
    _at(tick, _DUE + timedelta(minutes=25))
    assert await tick.worker() == 2
    assert tick.run.state is _S.PUBLISHED
    notice = tick.notifier.notices[-1]
    assert notice.extras is not None
    assert notice.extras.late_minutes == 25
    text = published_text(notice.permalink or "", notice.extras)
    assert "(publicado com atraso de 25 min)" in text.split("\n")[0]
    assert "Story" in text


# Scenario: A due tick never publishes twice
@pytest.mark.asyncio
async def test_due_tick_never_publishes_twice() -> None:
    tick = _tick()
    _at(tick, _DUE)
    await tick.worker()
    _at(tick, _DUE + timedelta(minutes=2))
    assert await tick.worker() == 0
    assert tick.gateway.opens == 1
    assert tick.gateway.finishes == 1
    assert tick.release.ids == [_PROJECT]
    assert len(tick.story.calls) == 1


@pytest.mark.asyncio
async def test_lost_compare_and_set_moves_nothing() -> None:
    tick = _tick()
    _at(tick, _DUE)
    tick.scheduled.raced = True
    assert await tick.sweep.tick() == 0
    assert tick.release.ids == []


# Scenario: A scheduled carousel that is no longer approved expires
@pytest.mark.asyncio
async def test_withdrawn_carousel_expires_without_publishing() -> None:
    tick = _tick()
    tick.source.snapshot = replace(_snapshot(), workflow_status="draft")
    _at(tick, _DUE + timedelta(minutes=1))
    assert await tick.worker() == 1
    assert tick.run.state is _S.EXPIRED
    assert tick.run.state_reason == REASON_SCHEDULE_WITHDRAWN
    assert tick.release.ids == []
    assert tick.gateway.opens == 0


@pytest.mark.asyncio
async def test_missing_carousel_expires() -> None:
    tick = _tick()
    tick.source.snapshot = None
    _at(tick, _DUE)
    await tick.sweep.tick()
    assert tick.run.state is _S.EXPIRED


@pytest.mark.asyncio
async def test_run_without_a_carousel_expires() -> None:
    tick = _tick(replace(_scheduled_run(), carousel_project_id=None))
    _at(tick, _DUE)
    await tick.sweep.tick()
    assert tick.run.state is _S.EXPIRED
    assert tick.release.ids == []


@pytest.mark.asyncio
async def test_failed_release_fails_and_tells_the_owner() -> None:
    tick = _tick()
    tick.release.ok = False
    _at(tick, _DUE)
    assert await tick.sweep.tick() == 1
    assert tick.run.state is _S.PUBLISH_FAILED
    assert tick.run.state_reason == REASON_SCHEDULE_RELEASE_FAILED
    notice = tick.notifier.notices[-1]
    assert notice.outcome == NOTICE_PUBLISH_FAILED
    assert notice.error_code == REASON_SCHEDULE_RELEASE_FAILED
    assert notice.offer_retry is False


@pytest.mark.asyncio
async def test_two_due_runs_both_move_earliest_first() -> None:
    tick = _tick()
    first = tick.run
    second = replace(_scheduled_run(_DUE - timedelta(hours=1)))
    tick.repo.runs[second.run_id] = second
    _at(tick, _DUE)
    assert await tick.sweep.tick() == 2
    assert tick.repo.runs[first.run_id].state is _S.PUBLISHING
    assert tick.repo.runs[second.run_id].state is _S.PUBLISHING
    assert tick.repo.commits == 2


@dataclass
class _Notices:
    ready: list[OwnerReadyNotice] = field(default_factory=list)

    async def notify_ready(self, notice: OwnerReadyNotice) -> None:
        self.ready.append(notice)


# Scenario: The 72 h review expiry never expires a scheduled run
@pytest.mark.asyncio
async def test_review_expiry_skips_scheduled_runs() -> None:
    repo = _Repo()
    old = _NOW - timedelta(hours=80)
    scheduled = replace(_scheduled_run(_NOW + timedelta(days=2)), updated_at=old)
    awaiting = replace(_run(), state=_S.AWAITING_OWNER, updated_at=old)
    repo.runs[scheduled.run_id] = scheduled
    repo.runs[awaiting.run_id] = awaiting
    recovery = RunRecovery(
        RecoveryDependencies(
            runs=repo,
            editorial=_Editorial(),
            notices=_Notices(),
            recovery=_Recovery(),
            clock=_Clock(),
            notifier_configured=True,
        )
    )
    await recovery.sweep()
    assert repo.runs[scheduled.run_id].state is _S.SCHEDULED
    assert repo.runs[awaiting.run_id].state is _S.EXPIRED
    assert repo.runs[awaiting.run_id].state_reason == REASON_OWNER_EXPIRED
