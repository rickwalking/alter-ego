"""Export outcomes and generation-timeout boundaries.

Feature: carousel_generation_log_ae0556.feature
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from structlog.testing import capture_logs

from rag_backend.application.services.carousel.nodes.export import (
    BilingualExportConfig,
    render_language,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.modules.generation_queue.application.generation_events import (
    generation_event_scope,
)
from rag_backend.modules.generation_queue.application.job_handler import VerdictKind
from rag_backend.modules.generation_queue.domain.generation_events import (
    EVENT_WRITE_TIMEOUT_SECONDS,
)
from rag_backend.modules.generation_queue.domain.models import GenerationKind
from tests.unit.modules.generation_queue.queue_fakes import (
    FakeStore,
    ScriptedExecutor,
    make_run,
    resume_run,
)
from tests.unit.modules.generation_queue.test_generation_event_steps_ae0556 import (
    PLANTED_TEXT,
    FakeRecorder,
    _run,
)
from tests.unit.modules.generation_queue.test_generation_events_ae0556 import (
    FakeEventRecorder,
    _handler,
    _LateProjectExecutor,
)


@dataclass
class CompletionProbe:
    calls: list[str]
    projects: list[str] = field(default_factory=list)

    async def completed(self, project_id: str, *, succeeded: bool = True) -> None:
        self.projects.append(project_id)
        self.calls.append("refresh" if succeeded else "refresh_failed")


def _config(
    export: AsyncMock, builder: MagicMock, tmp_path: Path
) -> BilingualExportConfig:
    return BilingualExportConfig(
        project=CarouselProject(topic="T", audience="A", niche="N"),
        slides_data=[],
        pt_html="",
        output_dir=tmp_path,
        export=export,
        pdf_builder=builder,
        language="en",
        html_content="",
    )


async def test_pdf_success_records_page_count(tmp_path: Path) -> None:
    """Scenario: A queued carousel has a complete generation timeline"""
    recorder = FakeRecorder()
    export = AsyncMock()
    export.export_slides = AsyncMock(side_effect=[["one.jpg"], ["hd-one.jpg"]])
    builder = MagicMock()
    builder.build = MagicMock(return_value=str(tmp_path / "slides.pdf"))
    async with generation_event_scope(_run(), recorder):
        await render_language(_config(export, builder, tmp_path))

    event = recorder.records[-1][1]
    assert event.event_type == "pdf_succeeded"
    assert event.outcome == "succeeded"
    assert event.details["page_count"] == 1


async def test_hd_failure_is_a_warning_not_a_pdf_failure(tmp_path: Path) -> None:
    """Scenario: A failed and retried run exposes safe failure and retry history"""
    recorder = FakeRecorder()
    export = AsyncMock()
    export.export_slides = AsyncMock(
        side_effect=[["one.jpg"], RuntimeError(PLANTED_TEXT)]
    )
    builder = MagicMock()
    builder.build = MagicMock(return_value=str(tmp_path / "slides.pdf"))
    async with generation_event_scope(_run(), recorder):
        await render_language(_config(export, builder, tmp_path))

    failures = [
        event for _, event in recorder.records if event.event_type == "pdf_failed"
    ]
    assert len(failures) == 1
    assert failures[0].outcome == "warning"
    assert failures[0].error_code == "hd_export_failed"
    assert PLANTED_TEXT not in json.dumps(failures[0].details)


async def test_pdf_build_failure_is_classified(tmp_path: Path) -> None:
    """Scenario: A failed and retried run exposes safe failure and retry history"""
    recorder = FakeRecorder()
    export = AsyncMock()
    export.export_slides = AsyncMock(side_effect=[["one.jpg"], ["hd-one.jpg"]])
    builder = MagicMock()
    builder.build = MagicMock(side_effect=ValueError(PLANTED_TEXT))
    async with generation_event_scope(_run(), recorder):
        await render_language(_config(export, builder, tmp_path))

    event = recorder.records[-1][1]
    assert event.event_type == "pdf_failed"
    assert event.outcome == "failed"
    assert event.error_code == "pdf_build_failed"
    assert PLANTED_TEXT not in json.dumps(event.details)


async def test_timeouts_preserve_generation_and_emit_safe_warnings() -> None:
    """Scenario: Event storage failures never break generation"""
    store = FakeStore()
    run = store.add(resume_run())
    recorder = FakeEventRecorder(delay=EVENT_WRITE_TIMEOUT_SECONDS * 2)
    started = time.monotonic()
    with capture_logs() as logs:
        verdict = await _handler(store, ScriptedExecutor(), recorder).handle(run.id)
    elapsed = time.monotonic() - started

    assert verdict.kind is VerdictKind.DONE
    assert store.runs[run.id].status.value == "succeeded"
    assert elapsed < EVENT_WRITE_TIMEOUT_SECONDS * 12
    failures = [
        entry for entry in logs if entry["event"] == "generation_event_store_failed"
    ]
    assert len(failures) == 4
    assert all(entry["error_type"] == "TimeoutError" for entry in failures)
    assert PLANTED_TEXT not in str(failures)


async def test_late_project_success_refreshes_resolved_project() -> None:
    """Scenario: A queued carousel has a complete generation timeline"""
    store = FakeStore()
    run = store.add(make_run())
    completion = CompletionProbe([])
    recorder = FakeEventRecorder(calls=completion.calls)

    verdict = await _handler(
        store,
        _LateProjectExecutor("p-late"),
        recorder,
        completion,
        GenerationKind.AUTOPILOT_DRIVE,
    ).handle(run.id)

    assert verdict.kind is VerdictKind.DONE
    assert completion.projects == ["p-late"]
    assert completion.calls[-1] == "refresh"


async def test_dead_letter_refresh_follows_failure_event() -> None:
    """Scenario: A failed and retried run exposes safe failure and retry history"""
    store = FakeStore()
    run = store.add(resume_run())
    completion = CompletionProbe([])
    recorder = FakeEventRecorder(calls=completion.calls)
    executor = ScriptedExecutor(error=ValueError(PLANTED_TEXT))

    verdict = await _handler(store, executor, recorder, completion).handle(run.id)

    assert verdict.kind is VerdictKind.HOLD
    assert completion.calls[-2:] == ["run_dead_letter", "refresh_failed"]
    assert completion.projects == ["p1"]


async def test_terminal_refresh_follows_event_and_state_persistence() -> None:
    """Scenario: A queued carousel has a complete generation timeline"""
    store = FakeStore()
    run = store.add(resume_run())
    calls: list[str] = []
    recorder = FakeEventRecorder(calls=calls)

    verdict = await _handler(
        store, ScriptedExecutor(), recorder, CompletionProbe(calls)
    ).handle(run.id)

    assert verdict.kind is VerdictKind.DONE
    assert store.runs[run.id].status.value == "succeeded"
    assert calls == [
        "run_started",
        "phase_started",
        "phase_succeeded",
        "run_succeeded",
        "refresh",
    ]
