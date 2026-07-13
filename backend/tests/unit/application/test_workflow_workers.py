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


def _settings() -> Settings:
    # Disable downstream DB-touching steps so the test isolates the error path.
    return Settings(
        workflow_worker_interval_seconds=0,
        workflow_alerts_enabled=False,
        workflow_auto_reject_enabled=False,
    )


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
        _settings(), cast(object, None), collaborators
    )
    assert log == ["reaper", "drift", "republish"]
    assert counters["republished"] == 0
