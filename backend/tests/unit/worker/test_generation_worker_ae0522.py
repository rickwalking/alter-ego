"""The worker entry: configuration guard, verdict mapping, loops, healthcheck."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pgqueuer.domain.errors import RetryRequested
from pgqueuer.domain.models import Job

from rag_backend.application.services.carousel.provider_errors import (
    classify_provider_error,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.generation_queue.application.dispatcher import DispatchReport
from rag_backend.modules.generation_queue.application.job_handler import (
    Verdict,
    VerdictKind,
)
from rag_backend.modules.generation_queue.domain.errors import DeadLetteredError
from rag_backend.modules.generation_queue.infrastructure.pgq_gateway import (
    job_payload,
    run_id_of,
)
from rag_backend.worker import healthcheck, periodic
from rag_backend.worker.main import (
    WorkerConfigError,
    is_provider_error,
    job_entrypoint,
    require_postgres_checkpointer,
)

_NOW = "2026-10-23T12:00:00+00:00"


def _settings(backend: str) -> Settings:
    return Settings(
        secret_key="s", anon_secret_key="a", carousel_checkpoint_backend=backend
    )


@pytest.mark.parametrize("backend", ["memory", "sqlite", "disabled"])
def test_worker_refuses_a_checkpointer_the_web_cannot_read(backend: str) -> None:
    """Scenario: The worker refuses to start without the Postgres checkpointer"""
    with pytest.raises(WorkerConfigError, match=backend):
        require_postgres_checkpointer(_settings(backend))


def test_worker_accepts_postgres() -> None:
    """Scenario: The worker refuses to start without the Postgres checkpointer"""
    require_postgres_checkpointer(_settings("Postgres"))


def test_provider_classifier_matches_the_shared_one() -> None:
    """Scenario: A transient failure retries with backoff and jitter"""
    error = RuntimeError("plain")
    assert is_provider_error(error) is (classify_provider_error(error) is not None)


@dataclass
class _Handler:
    verdict: Verdict
    seen: list[UUID] = field(default_factory=list)

    async def handle(self, run_id: UUID) -> Verdict:
        self.seen.append(run_id)
        return self.verdict


def _job(payload: bytes | None) -> Job:
    return Job.model_validate({
        "id": 1,
        "priority": 0,
        "created": _NOW,
        "updated": _NOW,
        "heartbeat": _NOW,
        "execute_after": _NOW,
        "status": "picked",
        "entrypoint": "carousel_generation",
        "payload": payload,
        "queue_manager_id": None,
        "headers": None,
    })


async def test_entrypoint_maps_verdicts_to_pgqueuer_signals() -> None:
    """Scenario: A drive with nothing to do comes back later"""
    run_id = uuid4()
    done = _Handler(Verdict(VerdictKind.DONE))
    await job_entrypoint(done)(_job(job_payload(run_id)))
    assert done.seen == [run_id]
    retry = _Handler(Verdict(VerdictKind.RETRY, timedelta(seconds=60)))
    with pytest.raises(RetryRequested) as raised:
        await job_entrypoint(retry)(_job(job_payload(run_id)))
    assert raised.value.delay == timedelta(seconds=60)
    with pytest.raises(DeadLetteredError):
        await job_entrypoint(_Handler(Verdict(VerdictKind.HOLD)))(
            _job(job_payload(run_id))
        )


async def test_entrypoint_ignores_a_foreign_payload() -> None:
    """Scenario: A permanent failure parks the run with its reason"""
    handler = _Handler(Verdict(VerdictKind.DONE))
    await job_entrypoint(handler)(_job(b"not-a-uuid"))
    await job_entrypoint(handler)(_job(None))
    assert handler.seen == []
    assert run_id_of(b"\xff") is None


def test_healthcheck_reads_the_liveness_file(tmp_path: Path) -> None:
    """Scenario: The worker container is capped and hardened"""
    alive = tmp_path / "alive"
    assert healthcheck.check(str(alive), time.time()) == healthcheck.EXIT_UNHEALTHY
    alive.touch()
    assert healthcheck.check(str(alive), time.time()) == healthcheck.EXIT_HEALTHY
    stale = time.time() - healthcheck.MAX_AGE_SECONDS - 5
    os.utime(alive, (stale, stale))
    assert healthcheck.check(str(alive), time.time()) == healthcheck.EXIT_UNHEALTHY


@dataclass
class _Dispatcher:
    stop: asyncio.Event
    passes: int = 0
    fail_first: bool = True

    async def run_once(self) -> DispatchReport:
        self.passes += 1
        if self.fail_first and self.passes == 1:
            raise ConnectionError
        self.stop.set()
        return DispatchReport()


async def test_dispatcher_loop_survives_a_failed_pass_and_marks_alive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: The dispatcher stages and hands over the queued work"""
    monkeypatch.setattr(periodic, "DISPATCH_INTERVAL_SECONDS", 0.01)
    stop = asyncio.Event()
    dispatcher = _Dispatcher(stop)
    alive = tmp_path / "alive"
    await asyncio.wait_for(
        periodic.run_dispatcher(dispatcher, lambda: stop, str(alive)), timeout=2
    )
    assert dispatcher.passes == 2
    assert alive.exists()


@dataclass
class _Step:
    name: str
    calls: list[str]
    fail: bool = False

    async def __call__(self, _session: object) -> int:
        self.calls.append(self.name)
        if self.fail:
            raise RuntimeError(self.name)
        return 1


class _Session:
    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def commit(self) -> None:
        return None


def _steps(calls: list[str], fail_reaper: bool) -> periodic.PeriodicSteps:
    reaper = type("Reaper", (), {"tick": _Step("reaper", calls, fail_reaper)})()
    drift = type("Drift", (), {"reconcile": _Step("drift", calls)})()
    republish = type("Republish", (), {"sweep": _Step("republish", calls)})()

    async def sweep() -> int:
        calls.append("sweep")
        raise RuntimeError

    bridge = type("Bridge", (), {"sweep": staticmethod(sweep)})()
    return periodic.PeriodicSteps(
        sessions=_Session,
        reaper=reaper,
        drift=drift,
        republish=republish,
        bridge=bridge,
    )


async def test_periodic_steps_run_in_order_and_isolated() -> None:
    """Scenario: The worker stops at the next phase boundary on shutdown"""
    calls: list[str] = []
    await periodic.run_periodic_once(_steps(calls, fail_reaper=True))
    assert calls == ["reaper", "drift", "republish", "sweep"]
    stop = asyncio.Event()
    stop.set()

    def signal() -> asyncio.Event:
        return stop

    await periodic.run_periodic(_steps(calls, fail_reaper=False), signal, 0.01)
    assert len(calls) == 4


def test_healthcheck_reads_the_worker_alive_file_setting() -> None:
    """Scenario: The worker container is capped and hardened"""
    assert (
        healthcheck.alive_file({"GENERATION_WORKER_ALIVE_FILE": "/x/alive"})
        == "/x/alive"
    )
    assert healthcheck.alive_file({}) == healthcheck.DEFAULT_WORKER_ALIVE_FILE
    assert healthcheck.alive_file({"GENERATION_WORKER_ALIVE_FILE": ""}) == (
        healthcheck.DEFAULT_WORKER_ALIVE_FILE
    )
