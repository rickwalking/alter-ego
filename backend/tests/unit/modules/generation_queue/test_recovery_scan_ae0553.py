"""Per-item isolation and safe observability for the daily recovery scan.

Feature: backend/tests/features/daily_recovery_scan_ae0553.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field

from asyncpg import UniqueViolationError
from sqlalchemy.exc import DBAPIError
from structlog.testing import capture_logs

from rag_backend.modules.generation_queue.application.recovery_scan import (
    DailyRecoveryScan,
    DailyScanDependencies,
    summary_text,
)
from rag_backend.modules.generation_queue.bootstrap import _NoParkedAutopilot
from rag_backend.modules.generation_queue.domain.recovery import (
    ParkedDrive,
    RecoveryFailure,
    ScanReport,
)
from tests.unit.modules.generation_queue.test_recovery_scan_ae0524 import (
    _Autopilot,
    _Clock,
    _drive,
    _scan,
    _Store,
)


@dataclass
class _OneFailure(_Autopilot):
    failing_run_id: str = ""
    error: Exception = field(default_factory=RuntimeError)
    seen: list[str] = field(default_factory=list)

    async def revive_dead_letter(self, drive: ParkedDrive) -> bool:
        self.seen.append(drive.autopilot_run_id)
        if drive.autopilot_run_id == self.failing_run_id:
            raise self.error
        return await super().revive_dead_letter(drive)


async def test_one_failing_dead_letter_does_not_stop_the_daily_scan() -> None:
    """Scenario: One failing dead letter does not stop the daily scan"""
    first, failed, last = _drive(), _drive(), _drive()
    reason = "database unavailable; prompt=never-log-this-content"
    autopilot = _OneFailure(
        failing_run_id=failed.autopilot_run_id,
        error=RuntimeError(reason),
    )
    store = _Store(parked=[first, failed, last])
    with capture_logs() as logs:
        report = await _scan(store, autopilot).run_once()
    assert autopilot.revived == [first.autopilot_run_id, last.autopilot_run_id]
    assert autopilot.seen == [
        first.autopilot_run_id,
        failed.autopilot_run_id,
        last.autopilot_run_id,
    ]
    assert store.purged_before
    assert report.recovered == 2
    assert report.queued == 3
    text = summary_text(report)
    assert failed.autopilot_run_id in text
    assert "RuntimeError" in text
    assert reason not in text
    item_logs = [
        entry
        for entry in logs
        if entry["event"] == "generation_daily_recovery_item_failed"
    ]
    assert len(item_logs) == 1
    entry = item_logs[0]
    assert entry["generation_run_id"] == str(failed.generation_run_id)
    assert entry["autopilot_run_id"] == failed.autopilot_run_id
    assert entry["error_type"] == "RuntimeError"
    assert "never-log-this-content" not in repr(logs)
    assert reason not in repr(logs)
    assert "exc_info" not in entry
    assert "exception" not in entry


async def test_each_failed_recovery_is_logged_without_content() -> None:
    """Scenario: Each failed recovery is logged without content"""

    class _AllFail(_Autopilot):
        async def revive_dead_letter(self, drive: ParkedDrive) -> bool:
            raise ValueError(f"prompt and payload for {drive.autopilot_run_id}")

    store = _Store(parked=[_drive(), _drive()])
    with capture_logs() as logs:
        report = await _scan(store, _AllFail()).run_once()
    item_logs = [
        entry
        for entry in logs
        if entry["event"] == "generation_daily_recovery_item_failed"
    ]
    assert len(report.failures) == 2
    assert len(item_logs) == 2
    assert {entry["error_type"] for entry in item_logs} == {"ValueError"}
    assert "prompt and payload" not in repr(logs)
    assert "exc_info" not in item_logs[0]
    assert "exception" not in item_logs[0]


async def test_disabled_autopilot_scans_preserve_one_attempt_marking() -> None:
    """Scenario: Disabled autopilot scans preserve one-attempt marking"""
    drive = _drive()
    store = _Store(parked=[drive])
    scan = DailyRecoveryScan(
        DailyScanDependencies(
            store=store,
            autopilot=_NoParkedAutopilot(store=store),
            clock=_Clock(),
        )
    )
    first = await scan.run_once()
    second = await scan.run_once()
    assert first.recovered == 0
    assert second.recovered == 0
    assert store.tried == {drive.generation_run_id}
    assert len(store.purged_before) == 2


async def test_failure_summary_accounts_for_overflow_and_empty_reasons() -> None:
    """Scenario: Failure summary accounts for overflow and empty reasons"""
    failures = tuple(
        RecoveryFailure(drive=_drive(), reason=f"reason {index}") for index in range(12)
    )
    text = summary_text(ScanReport(failures=failures))
    assert "mais 2" in text
    drive = _drive()
    autopilot = _OneFailure(failing_run_id=drive.autopilot_run_id, error=RuntimeError())
    report = await _scan(_Store(parked=[drive]), autopilot).run_once()
    empty_text = summary_text(report)
    assert "RuntimeError" in empty_text
    assert "RuntimeError: RuntimeError" not in empty_text


async def test_sqlalchemy_failure_reason_is_metadata_only() -> None:
    """Scenario: Recovery failures never expose SQL parameters."""
    sql = "UPDATE runs SET prompt = %(prompt)s WHERE id = %(run_id)s"
    secret = "secret-prompt-and-payload"
    error = DBAPIError(
        sql,
        {"prompt": secret, "run_id": "secret-run"},
        UniqueViolationError("duplicate sensitive detail"),
    )
    drive = _drive()
    autopilot = _OneFailure(failing_run_id=drive.autopilot_run_id, error=error)
    with capture_logs() as logs:
        report = await _scan(_Store(parked=[drive]), autopilot).run_once()
    text = summary_text(report)
    assert report.failures[0].reason == "DBAPIError: UniqueViolationError: 23505"
    assert logs[0]["error_type"] == "DBAPIError"
    assert logs[0]["dbapi_type"] == "UniqueViolationError"
    assert logs[0]["sqlstate"] == "23505"
    for sensitive in (sql, secret, "secret-run", "duplicate sensitive detail"):
        assert sensitive not in repr(logs)
        assert sensitive not in text


async def test_non_sql_failure_reason_is_exception_type_only() -> None:
    """Scenario: A non-SQL failure never falls back to its message."""
    drive = _drive()
    error = RuntimeError("prompt payload and secret parameters")
    autopilot = _OneFailure(failing_run_id=drive.autopilot_run_id, error=error)
    report = await _scan(_Store(parked=[drive]), autopilot).run_once()
    assert report.failures[0].reason == "RuntimeError"
    assert str(error) not in summary_text(report)
