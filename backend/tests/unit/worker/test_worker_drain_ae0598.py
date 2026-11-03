"""The deploy drain of the generation worker: flag, busy marker, gate, CLI.

Feature file: tests/features/deploy_drains_worker_ae0598.feature
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pgqueuer.domain.errors import RetryRequested
from pgqueuer.domain.models import Job

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.generation_queue.application.executors import (
    AutopilotDriveDependencies,
    AutopilotDriveExecutor,
    RecoveryDependencies,
)
from rag_backend.modules.generation_queue.application.job_handler import (
    Verdict,
    VerdictKind,
)
from rag_backend.modules.generation_queue.domain.ports import StepOutcome
from rag_backend.modules.generation_queue.infrastructure.pgq_gateway import (
    job_payload,
)
from rag_backend.worker import drain_cli
from rag_backend.worker.constants import (
    DRAIN_REASON,
    DRAIN_TTL_SECONDS,
    EXIT_BUSY,
    EXIT_OK,
    EXIT_USAGE,
)
from rag_backend.worker.drain import DrainFiles, DrainSwitch, JobGate, drive_stopping
from rag_backend.worker.main import (
    DRAIN_RETRY_DELAY,
    job_entrypoint,
    start_drain_switch,
)
from tests.unit.modules.generation_queue.queue_fakes import (
    FakeRecovery,
    FakeStepper,
    FakeStore,
    make_run,
)

_NOW = "2026-11-02T12:00:00+00:00"


def _files(tmp_path: Path) -> DrainFiles:
    return DrainFiles(drain=tmp_path / "drain", busy=tmp_path / "busy")


def _job(run_id: UUID) -> Job:
    return Job.model_validate({
        "id": 1,
        "priority": 0,
        "created": _NOW,
        "updated": _NOW,
        "heartbeat": _NOW,
        "execute_after": _NOW,
        "status": "picked",
        "entrypoint": "carousel_generation",
        "payload": job_payload(run_id),
        "queue_manager_id": None,
        "headers": None,
    })


@dataclass
class _Handler:
    """Records the runs it handled and whether the worker looked busy meanwhile."""

    switch: DrainSwitch
    fail: bool = False
    seen: list[UUID] = field(default_factory=list)
    busy_inside: list[bool] = field(default_factory=list)

    async def handle(self, run_id: UUID) -> Verdict:
        self.seen.append(run_id)
        self.busy_inside.append(self.switch.is_busy())
        if self.fail:
            raise RuntimeError("boom")
        return Verdict(VerdictKind.DONE)


async def test_a_drained_worker_refuses_the_job_and_puts_it_back(
    tmp_path: Path,
) -> None:
    """Scenario: A drained worker refuses to claim a job and puts it back"""
    switch = DrainSwitch(_files(tmp_path))
    switch.request()
    handler = _Handler(switch)
    with pytest.raises(RetryRequested) as raised:
        await job_entrypoint(handler, JobGate(switch))(_job(uuid4()))
    assert raised.value.delay == DRAIN_RETRY_DELAY
    assert raised.value.reason == DRAIN_REASON
    assert DRAIN_RETRY_DELAY.total_seconds() > 0
    assert handler.seen == []
    assert not switch.is_busy()


async def test_the_worker_claims_again_once_the_drain_is_cleared(
    tmp_path: Path,
) -> None:
    """Scenario: The worker claims jobs again once the drain is cleared"""
    switch = DrainSwitch(_files(tmp_path))
    handler = _Handler(switch)
    entry = job_entrypoint(handler, JobGate(switch))
    run_id = uuid4()
    switch.request()
    with pytest.raises(RetryRequested):
        await entry(_job(run_id))
    switch.clear()
    await entry(_job(run_id))
    assert handler.seen == [run_id]


async def test_the_worker_is_busy_while_a_job_is_in_flight(tmp_path: Path) -> None:
    """Scenario: The worker reports busy while a job is in flight"""
    switch = DrainSwitch(_files(tmp_path))
    handler = _Handler(switch)
    await job_entrypoint(handler, JobGate(switch))(_job(uuid4()))
    failing = _Handler(switch, fail=True)
    with pytest.raises(RuntimeError):
        await job_entrypoint(failing, JobGate(switch))(_job(uuid4()))
    assert handler.busy_inside == [True]
    assert failing.busy_inside == [True]
    assert not switch.is_busy()
    assert drain_cli.main(["idle"], _environ(tmp_path)) == EXIT_OK


async def test_busy_stays_until_the_last_job_in_flight_leaves(
    tmp_path: Path,
) -> None:
    """Scenario: The worker reports busy while a job is in flight"""
    switch = DrainSwitch(_files(tmp_path))
    gate = JobGate(switch)
    release = asyncio.Event()

    async def slow() -> None:
        async with gate.admit():
            await release.wait()

    task = asyncio.create_task(slow())
    await asyncio.sleep(0)
    async with gate.admit() as admitted:
        assert admitted
    assert switch.is_busy()
    assert drain_cli.main(["idle"], _environ(tmp_path)) == EXIT_BUSY
    release.set()
    await task
    assert not switch.is_busy()


async def test_a_stale_drain_flag_no_longer_pauses_the_worker(
    tmp_path: Path,
) -> None:
    """Scenario: A stale drain flag no longer pauses the worker"""
    files = _files(tmp_path)
    DrainSwitch(files).request()
    set_at = files.drain.stat().st_mtime
    fresh = DrainSwitch(files, clock=lambda: set_at + DRAIN_TTL_SECONDS)
    stale = DrainSwitch(files, clock=lambda: set_at + DRAIN_TTL_SECONDS + 1)
    assert fresh.is_draining()
    assert not stale.is_draining()
    handler = _Handler(stale)
    run_id = uuid4()
    await job_entrypoint(handler, JobGate(stale))(_job(run_id))
    assert handler.seen == [run_id]


def test_the_worker_clears_the_drain_flag_when_it_starts(tmp_path: Path) -> None:
    """Scenario: The worker clears the drain flag when it starts"""
    files = _files(tmp_path)
    files.drain.touch()
    files.busy.touch()
    settings = Settings(
        secret_key="s",
        anon_secret_key="a",
        generation_worker_drain_file=str(files.drain),
        generation_worker_busy_file=str(files.busy),
    )
    switch = start_drain_switch(settings)
    assert not files.drain.exists()
    assert not files.busy.exists()
    assert not switch.is_draining()
    assert not start_drain_switch(settings).is_draining()


@dataclass
class _DrainingStepper(FakeStepper):
    """Each step is one phase; the deploy sets the drain flag during the first."""

    switch: DrainSwitch | None = None

    async def step(self, run_id: str) -> int:
        if self.switch is not None:
            self.switch.request()
        return await super().step(run_id)


class _Tracker:
    async def begin(self, phase: str) -> None:
        del phase

    async def finish(self, phase: str) -> None:
        del phase

    async def track_step(self, phase: str, step: object) -> int:
        del phase
        assert callable(step)
        return int(await step())


async def test_a_drive_yields_at_the_next_phase_boundary_when_drained(
    tmp_path: Path,
) -> None:
    """Scenario: A drive in flight yields at the next phase boundary when the worker is drained"""
    switch = DrainSwitch(_files(tmp_path))
    stepper = _DrainingStepper(
        states=["generating", "generating", "awaiting_owner"], switch=switch
    )
    executor = AutopilotDriveExecutor(
        AutopilotDriveDependencies(
            stepper=stepper,
            recovery=RecoveryDependencies(store=FakeStore(), recovery=FakeRecovery()),
            stopping=drive_stopping(asyncio.Event(), switch),
        )
    )
    outcome = await executor.execute(make_run(), _Tracker())
    assert outcome is StepOutcome.YIELD
    assert stepper.steps == 1


def test_drive_stopping_follows_shutdown_and_drain(tmp_path: Path) -> None:
    """Scenario: A drive in flight yields at the next phase boundary when the worker is drained"""
    switch = DrainSwitch(_files(tmp_path))
    shutdown = asyncio.Event()
    stopping = drive_stopping(shutdown, switch)
    assert stopping() is False
    switch.request()
    assert stopping() is True
    switch.clear()
    shutdown.set()
    assert stopping() is True


def _environ(tmp_path: Path) -> dict[str, str]:
    return {
        "GENERATION_WORKER_DRAIN_FILE": str(tmp_path / "drain"),
        "GENERATION_WORKER_BUSY_FILE": str(tmp_path / "busy"),
    }


def test_the_cli_drains_reports_idle_and_clears(tmp_path: Path) -> None:
    """Scenario: The deploy waits until the worker is idle, then stops it"""
    environ = _environ(tmp_path)
    switch = DrainSwitch(_files(tmp_path))
    assert drain_cli.main(["drain"], environ) == EXIT_OK
    assert switch.is_draining()
    assert drain_cli.main(["idle"], environ) == EXIT_OK
    switch.mark_busy()
    assert drain_cli.main(["idle"], environ) == EXIT_BUSY
    assert drain_cli.main(["clear"], environ) == EXIT_OK
    assert not switch.is_draining()
    assert drain_cli.main(["clear"], environ) == EXIT_OK


@pytest.mark.parametrize("argv", [[], ["stop"], ["drain", "idle"]])
def test_the_cli_refuses_an_unknown_command(
    argv: list[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: A drain request the worker cannot answer never blocks the deploy"""
    assert drain_cli.main(argv, _environ(tmp_path)) == EXIT_USAGE
    assert "usage:" in capsys.readouterr().err
    assert not (tmp_path / "drain").exists()


def test_the_default_files_live_in_the_worker_tmp() -> None:
    """Scenario: The worker clears the drain flag when it starts"""
    files = DrainFiles.from_environ({})
    settings = Settings(secret_key="s", anon_secret_key="a")
    assert str(files.drain) == settings.generation_worker_drain_file
    assert str(files.busy) == settings.generation_worker_busy_file
    assert files.drain.parent == files.busy.parent
    assert files.drain != files.busy
    blank = DrainFiles.from_environ({"GENERATION_WORKER_DRAIN_FILE": ""})
    assert blank.drain == files.drain


def test_a_fresh_flag_is_draining_with_the_real_clock(tmp_path: Path) -> None:
    """Scenario: A drained worker refuses to claim a job and puts it back"""
    files = _files(tmp_path)
    switch = DrainSwitch(files)
    assert not switch.is_draining()
    switch.request()
    assert switch.is_draining()
    old = time.time() - DRAIN_TTL_SECONDS - 60
    os.utime(files.drain, (old, old))
    assert not switch.is_draining()
