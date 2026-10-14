"""Unit tests for the workflow worker loop (AE-0212).

Feature: tests/features/workflow_never_stuck.feature
Scenario: Worker tick failure renders a traceback
"""

from __future__ import annotations

import asyncio
import io

import pytest
import structlog

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services import scheduled_publish_service
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.application.workers import workflow_workers
from rag_backend.domain.protocols.workflow_timeout import StuckWorkflowAutoRejector
from rag_backend.infrastructure.config.settings import Settings

_BOOM = "scheduler exploded"
_WORKER_ERROR_EVENT = "workflow_workers_error"


class _NoopAutoRejector:
    """Stub auto-rejector; the error-path test never reaches a tick body."""

    async def auto_reject_stuck(self, db: object, timeout_hours: int) -> int:
        return 0


def _noop_factory(_event_service: WorkflowEventService) -> StuckWorkflowAutoRejector:
    return _NoopAutoRejector()


def _settings(**overrides: bool | int) -> Settings:
    # Disable downstream DB-touching steps so the test isolates the error path.
    values: dict[str, bool | int] = {
        "workflow_worker_interval_seconds": 0,
        "workflow_alerts_enabled": False,
        "workflow_auto_reject_enabled": False,
        "autopilot_enabled": False,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.asyncio
async def test_worker_error_renders_traceback(monkeypatch, test_engine) -> None:
    """A failing tick logs an event whose rendered output contains a traceback.

    Without the AE-0212 call-site ``exc_info=True`` the rendered event omits the
    exception entirely; this asserts the traceback is present.
    """
    monkeypatch.setattr(db_config, "c_engine", test_engine)
    buffer = io.StringIO()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(file=buffer),
        cache_logger_on_first_use=False,
    )
    monkeypatch.setattr(workflow_workers, "logger", structlog.get_logger())

    stop_event = asyncio.Event()

    async def _boom(self: object) -> int:
        stop_event.set()  # exit the loop after this (failing) tick
        raise RuntimeError(_BOOM)

    monkeypatch.setattr(
        scheduled_publish_service.ScheduledPublishService,
        "process_due_posts",
        _boom,
    )

    try:
        await workflow_workers.run_workflow_workers(
            _settings(),
            stop_event,
            workflow_workers.WorkflowWorkerServices(
                auto_rejector_factory=_noop_factory,
            ),
        )
    finally:
        structlog.reset_defaults()

    output = buffer.getvalue()
    assert _WORKER_ERROR_EVENT in output
    # format_exc_info renders the traceback under the "exception" key.
    assert "exception" in output
    assert "Traceback" in output
    assert _BOOM in output
    assert "RuntimeError" in output


class _RecordingReaper:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def tick(self, _db: object) -> int:
        self._log.append("reaper")
        return 0


class _RecordingReconciler:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def reconcile(self, _db: object) -> int:
        self._log.append("drift")
        return 0


class _RecordingSweeper:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def sweep(self, _db: object) -> int:
        self._log.append("republish")
        return 0


class _FakeSession:
    """Records the per-step commits and rollbacks of the worker tick."""

    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class _NoopNotifications:
    async def send_deadline_reminders(self, _db: object) -> int:
        return 0


class _NoopAlerts:
    async def check_and_alert(self, _db: object) -> int:
        return 0


@pytest.mark.asyncio
async def test_run_tick_sweeps_republish_after_drift_reconciler() -> None:
    """AE-0314 pinned ordering: reaper -> drift reconciler -> republish sweep."""
    from typing import cast

    log: list[str] = []
    collaborators = workflow_workers._TickCollaborators(
        notifications=cast(object, _NoopNotifications()),
        alerts=cast(object, _NoopAlerts()),
        auto_rejector=cast(object, _NoopAutoRejector()),
        stale_run_reaper=cast(object, _RecordingReaper(log)),
        drift_reconciler=cast(object, _RecordingReconciler(log)),
        republish_sweeper=cast(object, _RecordingSweeper(log)),
    )
    counters = await workflow_workers._run_tick(
        _settings(), cast(object, _FakeSession()), collaborators
    )
    assert log == ["reaper", "drift", "republish"]
    assert counters["republished"] == 0
    assert counters["instagram_runs"] == 0


class _RecordingPublish:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def tick(self, _db: object) -> int:
        self._log.append("instagram")
        return 1


@pytest.mark.asyncio
async def test_run_tick_publishes_instagram_after_the_other_workers() -> None:
    """AE-0357: the Instagram job is the last collaborator on the tick."""
    from typing import cast

    log: list[str] = []
    collaborators = workflow_workers._TickCollaborators(
        notifications=cast(object, _NoopNotifications()),
        alerts=cast(object, _NoopAlerts()),
        auto_rejector=cast(object, _NoopAutoRejector()),
        stale_run_reaper=cast(object, _RecordingReaper(log)),
        drift_reconciler=cast(object, _RecordingReconciler(log)),
        republish_sweeper=cast(object, _RecordingSweeper(log)),
        instagram_publish=cast(object, _RecordingPublish(log)),
    )
    counters = await workflow_workers._run_tick(
        _settings(), cast(object, _FakeSession()), collaborators
    )
    assert log == ["reaper", "drift", "republish", "instagram"]
    assert counters["instagram_runs"] == 1
    assert counters["autopilot_runs"] == 0


class _RecordingRunner:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def tick(self, _db: object) -> int:
        self._log.append("autopilot")
        return 1


@pytest.mark.asyncio
async def test_run_tick_runs_autopilot_after_instagram_when_enabled() -> None:
    """AE-0354: an enabled runner is the step after Instagram."""
    from typing import cast

    log: list[str] = []
    collaborators = workflow_workers._TickCollaborators(
        notifications=cast(object, _NoopNotifications()),
        alerts=cast(object, _NoopAlerts()),
        auto_rejector=cast(object, _NoopAutoRejector()),
        stale_run_reaper=cast(object, _RecordingReaper(log)),
        drift_reconciler=cast(object, _RecordingReconciler(log)),
        republish_sweeper=cast(object, _RecordingSweeper(log)),
        instagram_publish=cast(object, _RecordingPublish(log)),
        autopilot_runner=cast(object, _RecordingRunner(log)),
    )
    counters = await workflow_workers._run_tick(
        _settings(autopilot_enabled=True),
        cast(object, _FakeSession()),
        collaborators,
    )
    assert log == ["reaper", "drift", "republish", "instagram", "autopilot"]
    assert counters["autopilot_runs"] == 1


@pytest.mark.asyncio
async def test_run_tick_skips_autopilot_when_disabled() -> None:
    """Feature: tests/features/autopilot_runner.feature
    Scenario: Disabled worker skips the runner
    """
    from typing import cast

    log: list[str] = []
    collaborators = workflow_workers._TickCollaborators(
        notifications=cast(object, _NoopNotifications()),
        alerts=cast(object, _NoopAlerts()),
        auto_rejector=cast(object, _NoopAutoRejector()),
        stale_run_reaper=None,
        drift_reconciler=None,
        republish_sweeper=None,
        instagram_publish=cast(object, _RecordingPublish(log)),
        autopilot_runner=cast(object, _RecordingRunner(log)),
    )
    counters = await workflow_workers._run_tick(
        _settings(autopilot_enabled=False),
        cast(object, _FakeSession()),
        collaborators,
    )
    assert log == ["instagram"]
    assert counters["autopilot_runs"] == 0
    assert counters["telegram_notices"] == 0


class _RecordingTelegram:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def tick(self, _db: object) -> int:
        self._log.append("telegram")
        return 2


@pytest.mark.asyncio
async def test_run_tick_notifies_after_autopilot() -> None:
    """AE-0355: Telegram runs after the runner so a ready event is visible."""
    from typing import cast

    log: list[str] = []
    collaborators = workflow_workers._TickCollaborators(
        notifications=cast(object, _NoopNotifications()),
        alerts=cast(object, _NoopAlerts()),
        auto_rejector=cast(object, _NoopAutoRejector()),
        stale_run_reaper=None,
        drift_reconciler=None,
        republish_sweeper=None,
        instagram_publish=cast(object, _RecordingPublish(log)),
        autopilot_runner=cast(object, _RecordingRunner(log)),
        telegram_notify=cast(object, _RecordingTelegram(log)),
    )
    counters = await workflow_workers._run_tick(
        _settings(autopilot_enabled=True),
        cast(object, _FakeSession()),
        collaborators,
    )
    assert log == ["instagram", "autopilot", "telegram"]
    assert counters["telegram_notices"] == 2


class _RecordingCredentials:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def tick(self, _db: object) -> int:
        self._log.append("credentials")
        return 1


@pytest.mark.asyncio
async def test_run_tick_refreshes_credentials_before_instagram() -> None:
    """Feature: tests/features/autopilot_ig_token.feature
    Scenario: Token refreshed before expiry
    """
    from typing import cast

    log: list[str] = []
    collaborators = workflow_workers._TickCollaborators(
        notifications=cast(object, _NoopNotifications()),
        alerts=cast(object, _NoopAlerts()),
        auto_rejector=cast(object, _NoopAutoRejector()),
        stale_run_reaper=None,
        drift_reconciler=None,
        republish_sweeper=None,
        credential_refresh=cast(object, _RecordingCredentials(log)),
        instagram_publish=cast(object, _RecordingPublish(log)),
    )
    counters = await workflow_workers._run_tick(
        _settings(), cast(object, _FakeSession()), collaborators
    )
    assert log == ["credentials", "instagram"]
    assert counters["credential_refresh"] == 1
