"""The daily scan's re-notify step, on fakes.

Feature: tests/features/scan_escalation_renotice_ae0618.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

from structlog.testing import capture_logs

from rag_backend.modules.generation_queue.application.recovery_scan import (
    DailyRecoveryScan,
    DailyScanDependencies,
    summary_text,
)
from rag_backend.modules.generation_queue.bootstrap import (
    HandlerParts,
    _NoEscalationRenotifier,
    _renotifier,
)
from rag_backend.modules.generation_queue.domain.recovery import (
    RenotifyFailure,
    ScanReport,
)
from rag_backend.modules.generation_queue.infrastructure.escalation_renotifier import (
    SqlEscalationRenotifier,
)
from tests.unit.modules.generation_queue.test_recovery_scan_ae0524 import (
    _Autopilot,
    _Clock,
    _Store,
)

_SECRET = "prompt and payload"


@dataclass
class _Renotifier:
    runs: list[str] = field(default_factory=list)
    broken: set[str] = field(default_factory=set)
    moved_on: set[str] = field(default_factory=set)
    list_error: Exception | None = None
    tried: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)

    async def stuck_runs(self) -> list[str]:
        self.calls.append("stuck_runs")
        if self.list_error is not None:
            raise self.list_error
        return list(self.runs)

    async def renotify(self, run_id: str) -> bool:
        self.tried.append(run_id)
        if run_id in self.broken:
            raise ValueError(_SECRET)
        return run_id not in self.moved_on


def _scan(renotifier: _Renotifier, store: _Store | None = None) -> DailyRecoveryScan:
    return DailyRecoveryScan(
        DailyScanDependencies(
            store=store or _Store(),
            autopilot=_Autopilot(),
            renotifier=renotifier,
            clock=_Clock(),
        )
    )


async def test_each_stuck_run_is_renotified_and_counted() -> None:
    """Scenario: The summary carries the count"""
    runs = [str(uuid4()), str(uuid4())]
    report = await _scan(_Renotifier(runs=runs)).run_once()
    assert report.renotified == 2
    assert report.renotify_failures == ()
    assert "2" in summary_text(report).splitlines()[1]


async def test_a_run_that_moved_on_is_not_counted() -> None:
    """Scenario: A run that moved on after the listing is left alone"""
    runs = [str(uuid4()), str(uuid4())]
    renotifier = _Renotifier(runs=runs, moved_on={runs[0]})
    report = await _scan(renotifier).run_once()
    assert report.renotified == 1
    assert report.renotify_failures == ()


async def test_a_failing_item_does_not_stop_the_others() -> None:
    """Scenario: A failing item does not stop the others"""
    runs = [str(uuid4()), str(uuid4()), str(uuid4())]
    renotifier = _Renotifier(runs=runs, broken={runs[1]})
    with capture_logs() as logs:
        report = await _scan(renotifier).run_once()
    assert renotifier.tried == runs
    assert report.renotified == 2
    assert report.renotify_failures == (
        RenotifyFailure(run_id=runs[1], reason="ValueError"),
    )
    failed = [log for log in logs if log["event"] == "scan_renotify_item_failed"]
    assert [log["autopilot_run_id"] for log in failed] == [runs[1]]
    assert failed[0]["error_type"] == "ValueError"
    assert _SECRET not in repr(logs)
    text = summary_text(report)
    assert runs[1] in text
    assert "ValueError" in text
    assert _SECRET not in text


async def test_a_failing_listing_does_not_stop_the_scan() -> None:
    """Scenario: A failing listing does not stop the scan"""
    store = _Store()
    renotifier = _Renotifier(list_error=ValueError(_SECRET))
    report = await _scan(renotifier, store).run_once()
    assert store.purged_before
    assert report.renotified == 0
    assert report.renotify_failures == (
        RenotifyFailure(run_id="stuck_runs", reason="ValueError"),
    )
    assert "ValueError" in summary_text(report)


async def test_the_step_runs_once_per_scan() -> None:
    renotifier = _Renotifier()
    await _scan(renotifier).run_once()
    assert renotifier.calls == ["stuck_runs"]


def test_a_quiet_days_summary_does_not_change() -> None:
    """Scenario: A quiet day's summary does not change"""
    assert summary_text(ScanReport(recovered=2, still_dead=1, queued=5)) == (
        "🌅 Varredura diária da fila: 2 recolocado(s) na fila, "
        "1 parado(s) nos últimos 7 dias, 5 na fila agora."
    )


def test_the_count_line_is_exact() -> None:
    """Scenario: The summary carries the count"""
    lines = summary_text(ScanReport(renotified=3)).splitlines()
    assert lines[1:] == ["🔁 Aviso de escalada reenviado a 3 execução(ões) parada(s)."]


def test_failures_are_listed_up_to_the_limit() -> None:
    failures = tuple(
        RenotifyFailure(run_id=f"run-{index}", reason="ValueError")
        for index in range(12)
    )
    line = summary_text(ScanReport(renotify_failures=failures)).splitlines()[1]
    assert line.startswith("Falhas ao reenviar aviso: run-0: ValueError; ")
    assert "run-9: ValueError" in line
    assert "run-10" not in line
    assert line.endswith("… e mais 2")


def test_the_count_comes_before_the_failures_and_the_parked_projects() -> None:
    report = ScanReport(
        renotified=1,
        renotify_failures=(RenotifyFailure(run_id="r", reason="E"),),
        interactive=("Projeto",),
    )
    lines = summary_text(report).splitlines()
    assert "reenviado" in lines[1]
    assert lines[2].startswith("Falhas ao reenviar aviso")
    assert lines[3].startswith("Projetos do painel")


async def test_with_driving_off_nothing_is_renotified() -> None:
    """Scenario: With autopilot driving off the step does nothing"""
    off = _NoEscalationRenotifier()
    assert await off.stuck_runs() == []
    assert await off.renotify("any") is False


async def test_a_listing_error_never_uses_the_exception_text() -> None:
    renotifier = _Renotifier(list_error=RuntimeError(_SECRET))
    with capture_logs() as logs:
        report = await _scan(renotifier).run_once()
    assert _SECRET not in repr(logs)
    assert _SECRET not in summary_text(report)


def test_driving_autopilot_wires_the_real_renotifier() -> None:
    """Scenario: An eligible escalated run gets one notice with the carousel Retry"""
    parts = SimpleNamespace(drive_autopilot=True, sessions=None)
    assert isinstance(_renotifier(cast(HandlerParts, parts)), SqlEscalationRenotifier)


def test_with_driving_off_the_no_op_is_wired() -> None:
    """Scenario: With autopilot driving off the step does nothing"""
    parts = SimpleNamespace(drive_autopilot=False, sessions=None)
    assert isinstance(_renotifier(cast(HandlerParts, parts)), _NoEscalationRenotifier)
