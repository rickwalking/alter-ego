"""Per-item isolation and safe observability for the daily recovery scan.

Feature: backend/tests/features/daily_recovery_scan_ae0553.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field

from structlog.testing import capture_logs

from rag_backend.modules.generation_queue.application.recovery_scan import summary_text
from rag_backend.modules.generation_queue.domain.recovery import ParkedDrive
from tests.unit.modules.generation_queue.test_recovery_scan_ae0524 import (
    _Autopilot,
    _drive,
    _scan,
    _Store,
)


@dataclass
class _OneFailure(_Autopilot):
    failing_run_id: str = ""
    reason: str = ""
    seen: list[str] = field(default_factory=list)

    async def revive_dead_letter(self, drive: ParkedDrive) -> bool:
        self.seen.append(drive.autopilot_run_id)
        if drive.autopilot_run_id == self.failing_run_id:
            raise RuntimeError(self.reason)
        return await super().revive_dead_letter(drive.autopilot_run_id)


async def test_one_failing_dead_letter_does_not_stop_the_daily_scan() -> None:
    """Scenario: One failing dead letter does not stop the daily scan"""
    first, failed, last = _drive(), _drive(), _drive()
    reason = "database unavailable; prompt=never-log-this-content"
    autopilot = _OneFailure(
        failing_run_id=failed.autopilot_run_id,
        reason=reason,
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
    assert "database unavailable" in text
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
