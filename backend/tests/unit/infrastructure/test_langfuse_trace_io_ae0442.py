"""Langfuse traces record input, output and useful names (AE-0442).

Gherkin: tests/features/langfuse_trace_io_ae0442.feature
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from rag_backend.application.services.blog_workflow_observability import (
    BlogPhaseScope,
    blog_phase_trace,
)
from rag_backend.application.services.blog import blog_generation_runner
from rag_backend.domain.constants.blog_editor import PHASE_BLOG_SECTION_IMAGE
from rag_backend.domain.constants.blog_generation import (
    AGENT_BLOG_IMAGES,
    AGENT_BLOG_WRITER,
    PHASE_BLOG_GENERATION,
)
from rag_backend.domain.models.carousels import ReviewEventParams
from rag_backend.infrastructure import monitoring_langfuse
from rag_backend.infrastructure.langfuse_phase_trace import (
    WorkflowTraceScope,
    generation_run_name,
    phase_trace,
    workflow_trace_scope,
)
from rag_backend.infrastructure.monitoring_langfuse import (
    _TraceConfig,
    create_workflow_trace,
    get_langfuse_runnable_config,
    propagate_attributes,
    record_human_review,
)
from tests.langfuse_trace_fakes import install_trace_collector

_CAROUSEL_SCOPE = WorkflowTraceScope(
    project_id="p-1",
    user_id="owner-1",
    agent_name="editorial_workflow",
    content_type="carousel",
)
_BLOG_SCOPE = WorkflowTraceScope(
    project_id="post-9",
    user_id="owner-1",
    agent_name=AGENT_BLOG_IMAGES,
    content_type="blog_post",
)
_TELEGRAM_SECRET = "/bot123456:AAH-secret-token"
_GRAPH_SECRET = "access_token=graph-secret"
_SECRET_TEXT = f"failed {_TELEGRAM_SECRET} {_GRAPH_SECRET}"


def _json(value: object) -> str:
    return json.dumps(value, default=str)


class TestPhaseTraceIO:
    # Scenario: A phase trace records its brief as input and its result as output
    def test_trace_and_span_carry_brief_and_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        collector = install_trace_collector(monkeypatch)

        with (
            workflow_trace_scope(_CAROUSEL_SCOPE),
            phase_trace(
                {"phase": "content"},
                input={
                    "topic": "IA",
                    "attempt": 2,
                    "model_queue": "deepseek-v4.1-flash",
                },
            ) as trace,
        ):
            trace.set_output({"status": "completed", "slide_count": 7})

        recorded = collector.traces[0]
        assert recorded.name == "workflow_content"
        assert recorded.trace_name == "workflow_content"
        assert recorded.input == {
            "project_id": "p-1",
            "phase": "content",
            "content_type": "carousel",
            "agent_name": "editorial_workflow",
            "topic": "IA",
            "attempt": 2,
            "model_queue": "deepseek-v4.1-flash",
        }
        assert recorded.output == {"status": "completed", "slide_count": 7}
        assert recorded.span_input == recorded.input
        assert recorded.span_output == recorded.output
        assert recorded.user_id == "owner-1"
        assert recorded.session_id == "p-1"
        assert "phase:content" in recorded.tags
        assert collector.flushes == 1

    # Scenario: A failing phase records a redacted error as output
    def test_failure_records_error_output_and_reraises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        collector = install_trace_collector(monkeypatch)

        with pytest.raises(RuntimeError, match="provider down"):
            with phase_trace({"phase": "content"}) as trace:
                assert trace.name == "workflow_content"
                raise RuntimeError(f"provider down {_SECRET_TEXT}")

        recorded = collector.traces[0]
        output = recorded.output
        assert isinstance(output, dict)
        assert output["status"] == "error"
        assert output["error_type"] == "RuntimeError"
        assert output["error_message"].startswith("provider down")
        assert _TELEGRAM_SECRET not in output["error_message"]
        assert _GRAPH_SECRET not in output["error_message"]
        assert recorded.span_output == output
        assert recorded.level == "ERROR"
        assert collector.flushes == 1

    # Scenario: A phase flush happens even when the phase fails
    def test_flush_happens_once_per_phase(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        collector = install_trace_collector(monkeypatch)

        for _ in range(2):
            with phase_trace({"phase": "images"}):
                pass

        assert collector.flushes == 2

    def test_no_client_yields_a_handle_without_tracing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "rag_backend.infrastructure.langfuse_phase_trace.get_langfuse_client",
            lambda: None,
        )

        with phase_trace({"phase": "outline"}) as trace:
            trace.set_output({"status": "completed"})

        assert trace.span is None


class TestBlogGenerationTrace:
    # Scenario: A blog generation trace carries the writer brief and the article summary
    def test_blog_phase_trace_carries_brief_and_summary(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        collector = install_trace_collector(monkeypatch)
        scope = BlogPhaseScope(
            project_id="post-9",
            user_id="owner-1",
            phase=PHASE_BLOG_GENERATION,
            agent_name=AGENT_BLOG_WRITER,
        )

        with blog_phase_trace(
            scope,
            input={
                "post_id": "post-9",
                "title": "IA no trabalho",
                "section_count": 5,
            },
        ) as trace:
            trace.set_output({
                "status": "completed",
                "section_count": 5,
                "voice_score": 82.5,
            })

        recorded = collector.traces[0]
        assert recorded.trace_name == "workflow_blog_generation"
        assert recorded.input["post_id"] == "post-9"
        assert recorded.input["title"] == "IA no trabalho"
        assert recorded.input["section_count"] == 5
        assert recorded.output == {
            "status": "completed",
            "section_count": 5,
            "voice_score": 82.5,
        }
        assert "content:blog_post" in recorded.tags


class TestGenerationNames:
    # Scenario: A generation is named after the agent, phase and detail
    def test_run_name_comes_from_the_active_phase_and_detail(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            monitoring_langfuse, "get_langfuse_handler", lambda: [MagicMock()]
        )

        with (
            workflow_trace_scope(_CAROUSEL_SCOPE),
            phase_trace({"phase": "content"}),
            generation_run_name("slide 3"),
        ):
            config = get_langfuse_runnable_config()

        assert config["run_name"] == "carousel.content slide 3"

    # Scenario: A generation outside a phase trace still gets a stable name
    def test_run_name_defaults_without_a_phase(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            monitoring_langfuse, "get_langfuse_handler", lambda: [MagicMock()]
        )

        config = get_langfuse_runnable_config()

        assert config["run_name"] == "llm.call"

    def test_no_handler_means_no_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(monitoring_langfuse, "get_langfuse_handler", lambda: None)

        assert get_langfuse_runnable_config() == {}


class TestReviewEvents:
    # Scenario: A human review is recorded in a named trace with input and output
    def test_review_event_lives_in_a_named_trace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        collector = install_trace_collector(monkeypatch)

        record_human_review(
            params=ReviewEventParams(
                phase="content",
                action="approve",
                reviewer_id="reviewer-1",
                time_to_respond=None,
                feedback=None,
            ),
            project_id="p-1",
            user_id="reviewer-1",
        )

        recorded = collector.traces[0]
        assert recorded.trace_name == "workflow_review"
        assert len(recorded.events) == 1
        assert recorded.events[0].name == "human_review_content_completed"
        assert recorded.input["action"] == "approve"
        assert recorded.output == {"status": "recorded", "action": "approve"}
        assert recorded.user_id == "reviewer-1"
        assert collector.flushes == 1

    def test_review_event_is_a_noop_without_langfuse(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "rag_backend.infrastructure.langfuse_phase_trace.get_langfuse_client",
            lambda: None,
        )

        record_human_review(
            params=ReviewEventParams(
                phase="content",
                action="approve",
                reviewer_id="reviewer-1",
                time_to_respond=None,
                feedback=None,
            ),
            project_id="p-1",
            user_id="reviewer-1",
        )


class TestWorkflowTrace:
    def test_reuses_the_active_phase_span(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        collector = install_trace_collector(monkeypatch)

        with (
            workflow_trace_scope(_CAROUSEL_SCOPE),
            phase_trace({"phase": "content"}) as phase,
        ):
            trace = create_workflow_trace(
                config=_TraceConfig(
                    project_id="p-1",
                    user_id="owner-1",
                    content_type="carousel",
                )
            )

        assert trace is phase.span
        assert len(collector.traces) == 1
        assert collector.traces[0].trace_name == "workflow_content"


class TestNestedPropagation:
    # Scenario: A nested propagation helper reuses the outer phase span
    def test_nested_propagation_keeps_the_outer_span_and_actor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        collector = install_trace_collector(monkeypatch)

        with (
            workflow_trace_scope(_BLOG_SCOPE),
            phase_trace({"phase": PHASE_BLOG_SECTION_IMAGE}) as outer,
            propagate_attributes(
                metadata={
                    "post_id": "post-9",
                    "phase": PHASE_BLOG_SECTION_IMAGE,
                    "content_type": "blog_post",
                }
            ) as inner,
        ):
            assert inner is outer

        assert len(collector.traces) == 1
        recorded = collector.traces[0]
        assert recorded.metadata["project_id"] == "post-9"
        assert recorded.metadata["user_id"] == "owner-1"
        assert recorded.metadata["agent_name"] == AGENT_BLOG_IMAGES
        assert recorded.metadata["post_id"] == "post-9"
        assert collector.flushes == 1


class TestSecretRedaction:
    # Scenario: Captured payloads never contain secrets
    def test_input_and_output_are_redacted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        collector = install_trace_collector(monkeypatch)

        with phase_trace(
            {"phase": "content"},
            input={"note": _SECRET_TEXT},
        ) as trace:
            trace.set_output({"note": _SECRET_TEXT})

        recorded = collector.traces[0]
        captured = _json({"input": recorded.input, "output": recorded.output})
        assert _TELEGRAM_SECRET not in captured
        assert _GRAPH_SECRET not in captured
        assert "/bot<redacted>" in captured
        assert "access_token=<redacted>" in captured


class TestBackgroundFlush:
    # Scenario: A finished background runner flushes Langfuse
    @pytest.mark.asyncio
    async def test_blog_generation_runner_flushes_when_done(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        flushes: list[bool] = []
        monkeypatch.setattr(
            blog_generation_runner, "flush_langfuse", lambda: flushes.append(True)
        )
        service = MagicMock()
        service.run = MagicMock()

        async def run(_job: object) -> None:
            return None

        service.run = run

        await blog_generation_runner._run(service, MagicMock())

        assert flushes == [True]
