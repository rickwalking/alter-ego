"""Notable generation steps emit safe, correlated timeline events.

Feature: carousel_generation_log_ae0556.feature
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.nodes.export import (
    BilingualExportConfig,
    render_language,
)
from rag_backend.application.services.carousel.nodes.images import (
    ImageGenerationConfig,
    run_images,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.carousel_run import (
    CarouselRunContext,
    carousel_run_epoch_var,
)
from rag_backend.infrastructure.langfuse_phase_trace import PhaseTrace, phase_trace
from rag_backend.modules.generation_queue.application.generation_events import (
    generation_event_scope,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEventInput,
    GenerationEventRun,
)
from rag_backend.modules.generation_queue.domain.models import GenerationKind
from rag_backend.modules.generation_queue.events_public import (
    WorkflowOutcomeObservation,
    record_phase_artifacts,
    record_workflow_outcome,
)
from rag_backend.modules.image_bridge.domain.exceptions import ImageBridgeJobError
from rag_backend.modules.image_bridge.domain.models import JobFailure, JobSuccess
from tests.langfuse_trace_fakes import install_trace_collector
from tests.unit.application.test_phase5_parallel import (
    _project,
    _registry_with_image_service,
    _slide_data,
)
from tests.unit.modules.image_bridge.support import (
    FakeClock,
    FakeWebhook,
    png_bytes,
    sqlite_repository,
)
from tests.unit.modules.image_bridge.test_image_bridge_waiter import (
    _answer_each_job,
    _service,
)

PLANTED_TEXT = "private slide text and prompt"


@dataclass
class FakeRecorder:
    records: list[tuple[GenerationEventRun, GenerationEventInput]] = field(
        default_factory=list
    )

    async def record(
        self, run: GenerationEventRun, event: GenerationEventInput
    ) -> bool:
        self.records.append((run, event))
        return True


def _run() -> GenerationEventRun:
    return GenerationEventRun(
        id=uuid4(),
        kind=GenerationKind.WORKFLOW_RESUME,
        carousel_project_id="p1",
    )


def _trace() -> PhaseTrace:
    return PhaseTrace(
        name="workflow_content",
        span=None,
        trace_input=None,
        metadata={},
        tags=(),
        user_id=None,
        session_id="p1",
        trace_id="b" * 32,
        trace_url="https://cloud.langfuse.com/project/p1/traces/" + "b" * 32,
    )


async def test_phase_steps_keep_scores_counts_and_trace_without_content() -> None:
    """Scenario: A queued carousel has a complete generation timeline"""
    recorder = FakeRecorder()
    result = {
        "persona_scores": {
            "slide_1": {"overall": 8.5, "suggestions": PLANTED_TEXT},
            "slide_2": {"overall": 0, "suggestions": PLANTED_TEXT},
        },
        "content_gate_validation": {
            "validation_status": "failed",
            "blocking": [{"code": "copy_truncated"}],
            "violations": [{"message": PLANTED_TEXT, "text": PLANTED_TEXT}],
        },
    }
    async with generation_event_scope(_run(), recorder):
        await record_phase_artifacts("content", result, _trace())

    assert [event.event_type for _, event in recorder.records] == [
        "phase_artifacts",
        "persona_scored",
        "content_gate",
    ]
    persona = recorder.records[1][1]
    gate = recorder.records[2][1]
    assert persona.details == {
        "lowest_score": 85.0,
        "scored_count": 1,
        "unscored_count": 1,
    }
    assert gate.details["violation_count"] == 1
    assert gate.details["blocking_count"] == 1
    assert gate.outcome == "failed"
    assert all(event.langfuse_trace_id == "b" * 32 for _, event in recorder.records)
    assert PLANTED_TEXT not in json.dumps([
        event.details for _, event in recorder.records
    ])


async def test_phase_steps_work_without_langfuse() -> None:
    """Scenario: Langfuse trace links are optional"""
    recorder = FakeRecorder()
    async with generation_event_scope(_run(), recorder):
        await record_phase_artifacts("outline", {"outline": []}, None)

    assert len(recorder.records) == 1
    event = recorder.records[0][1]
    assert event.outcome == "succeeded"
    assert event.langfuse_trace_id is None
    assert event.langfuse_trace_url is None


async def test_workflow_failure_is_distinct_from_queue_completion() -> None:
    """Scenario: A failed and retried run exposes safe failure and retry history"""
    recorder = FakeRecorder()
    async with generation_event_scope(_run(), recorder):
        await record_workflow_outcome(
            WorkflowOutcomeObservation(
                project_id="p1",
                phase="content",
                outcome="failed",
                error_code="background_resume_failed",
                error_type="RuntimeError",
            )
        )

    event = recorder.records[0][1]
    assert event.event_type == "workflow_failed"
    assert event.outcome == "failed"
    assert event.error_code == "background_resume_failed"
    assert event.details == {"error_type": "RuntimeError"}


async def test_image_bridge_emits_safe_job_timeline(tmp_path: Path) -> None:
    """Scenario: A queued carousel has a complete generation timeline"""
    webhook, clock = FakeWebhook(), FakeClock()
    recorder = FakeRecorder()
    output = tmp_path / "slide_1.jpg"
    async with sqlite_repository() as repo:
        clock.on_sleep = _answer_each_job(repo, webhook, clock)
        service = _service(repo, (webhook, clock))
        token = carousel_run_epoch_var.set(CarouselRunContext("p1", 3))
        try:
            async with generation_event_scope(_run(), recorder):
                await service.generate_image(PLANTED_TEXT, str(output))
        finally:
            carousel_run_epoch_var.reset(token)

    assert [event.event_type for _, event in recorder.records] == [
        "image_job_started",
        "image_job_succeeded",
    ]
    started, finished = (event for _, event in recorder.records)
    assert started.details["model"] == "gpt-image-2"
    assert started.details["size"] == "1536x1024"
    assert started.details["image_job_id"] == finished.details["image_job_id"]
    assert finished.duration_ms is not None
    assert finished.outcome == "succeeded"
    assert PLANTED_TEXT not in json.dumps([started.details, finished.details])
    assert "callback_token" not in json.dumps([started.details, finished.details])


async def test_missing_image_result_records_safe_job_failure(tmp_path: Path) -> None:
    """Scenario: A failed and retried run exposes safe failure and retry history"""
    webhook, clock = FakeWebhook(), FakeClock()
    recorder = FakeRecorder()
    async with sqlite_repository() as repo:
        service = _service(repo, (webhook, clock))

        async def consume_result() -> None:
            job_id = webhook.requests[0].job_id
            await repo.succeed(JobSuccess(job_id, png_bytes(), clock.now()))
            await repo.take_image(job_id)

        clock.on_sleep = consume_result
        with pytest.raises(ImageBridgeJobError):
            async with generation_event_scope(_run(), recorder):
                await service.generate_image("p", str(tmp_path / "missing.jpg"))

    event = recorder.records[-1][1]
    assert event.event_type == "image_job_failed"
    assert event.error_code == "no_image"
    assert event.outcome == "failed"


async def test_standard_export_failure_records_safe_pdf_event(tmp_path: Path) -> None:
    """Scenario: A failed and retried run exposes safe failure and retry history"""
    recorder = FakeRecorder()
    export = AsyncMock()
    export.export_slides = AsyncMock(side_effect=RuntimeError(PLANTED_TEXT))
    config = BilingualExportConfig(
        project=CarouselProject(topic="T", audience="A", niche="N"),
        slides_data=[],
        pt_html="",
        output_dir=tmp_path,
        export=export,
        language="en",
        html_content="",
    )
    with pytest.raises(RuntimeError):
        async with generation_event_scope(_run(), recorder):
            await render_language(config)

    event = recorder.records[-1][1]
    assert event.event_type == "pdf_failed"
    assert event.error_code == "slides_export_failed"
    assert event.outcome == "failed"
    assert event.details["error_type"] == "RuntimeError"
    assert PLANTED_TEXT not in json.dumps(event.details)


async def test_provider_slide_failure_records_before_reraise(tmp_path: Path) -> None:
    """Scenario: A failed and retried run exposes safe failure and retry history"""
    recorder = FakeRecorder()
    image_service = AsyncMock()
    image_service.generate_image = AsyncMock(side_effect=RuntimeError(PLANTED_TEXT))
    registry, repo = _registry_with_image_service(image_service)
    config = ImageGenerationConfig(
        project=_project(tmp_path),
        slides=[_slide_data(1)],
        output_dir=tmp_path,
        repo=repo,
        image_registry=registry,
    )
    with pytest.raises(RuntimeError):
        async with generation_event_scope(_run(), recorder):
            await run_images(config)

    event_types = [event.event_type for _, event in recorder.records]
    assert event_types == ["image_slide_failed"]
    event = recorder.records[0][1]
    assert event.outcome == "failed"
    assert event.details["slide_index"] == 1
    assert PLANTED_TEXT not in json.dumps(event.details)


async def test_external_callback_error_code_is_classified(tmp_path: Path) -> None:
    """Scenario: Stored events exclude sensitive failure content"""
    webhook, clock = FakeWebhook(), FakeClock()
    recorder = FakeRecorder()
    external_code = "sk-planted-secret"
    async with sqlite_repository() as repo:
        service = _service(repo, (webhook, clock))

        async def refuse() -> None:
            job_id = webhook.requests[0].job_id
            await repo.fail(JobFailure(job_id, external_code, "no", clock.now()))

        clock.on_sleep = refuse
        with pytest.raises(ImageBridgeJobError):
            async with generation_event_scope(_run(), recorder):
                await service.generate_image("p", str(tmp_path / "refused.jpg"))

    event = recorder.records[-1][1]
    assert event.error_code == "unknown_error"
    assert external_code not in json.dumps(event.details)


async def test_sdk_trace_populates_optional_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Langfuse trace links are optional"""
    install_trace_collector(monkeypatch)
    recorder = FakeRecorder()
    async with generation_event_scope(_run(), recorder):
        with phase_trace({"phase": "content", "project_id": "p1"}) as trace:
            await record_phase_artifacts("content", {}, trace)

    event = recorder.records[0][1]
    assert event.langfuse_trace_id == "c" * 32
    assert event.langfuse_trace_url == (
        "https://langfuse.test/project/test-project/traces/" + "c" * 32
    )


async def test_sdk_trace_failure_drops_link_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Langfuse trace links are optional"""
    collector = install_trace_collector(monkeypatch)

    def fail_trace_id() -> str:
        raise RuntimeError("sdk unavailable")

    monkeypatch.setattr(collector, "get_current_trace_id", fail_trace_id)
    recorder = FakeRecorder()
    async with generation_event_scope(_run(), recorder):
        with phase_trace({"phase": "content", "project_id": "p1"}) as trace:
            await record_phase_artifacts("content", {}, trace)

    event = recorder.records[0][1]
    assert event.langfuse_trace_id is None
    assert event.langfuse_trace_url is None
