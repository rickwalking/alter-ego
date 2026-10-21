"""Phase trace attributes and the Langfuse span wiring (AE-0390).

Gherkin: tests/features/workflow_tracing_and_heartbeat.feature
"""

from __future__ import annotations

import pytest

from rag_backend.domain.constants.langfuse_tracing import TRACE_REQUIRED_FIELDS
from rag_backend.infrastructure import langfuse_phase_trace
from rag_backend.infrastructure.langfuse_phase_trace import (
    WorkflowTraceScope,
    build_phase_trace,
    current_trace_scope,
    phase_trace,
    workflow_trace_scope,
)
from rag_backend.infrastructure.monitoring_langfuse import propagate_attributes
from tests.langfuse_trace_fakes import install_trace_collector

_AUTOPILOT = WorkflowTraceScope(
    project_id="p-1", agent_name="autopilot", content_type="carousel"
)


class TestBuildPhaseTrace:
    # Scenario: Missing attributes never drop a metadata key
    def test_defaults_fill_every_required_key(self) -> None:
        attributes = build_phase_trace({"phase": "outline"})

        assert attributes.name == "workflow_outline"
        assert set(TRACE_REQUIRED_FIELDS) <= set(attributes.metadata)
        assert attributes.metadata["project_id"] == "unknown"
        assert attributes.metadata["user_id"] == "unknown"
        assert attributes.metadata["agent_name"] == "editorial_workflow"
        assert attributes.metadata["content_type"] == "carousel"
        assert attributes.user_id is None
        assert attributes.tags == (
            "phase:outline",
            "agent:editorial_workflow",
            "content:carousel",
        )

    def test_missing_phase_reads_unknown(self) -> None:
        attributes = build_phase_trace({})

        assert attributes.name == "workflow_unknown"
        assert attributes.tags[0] == "phase:unknown"

    def test_scope_supplies_the_actor(self) -> None:
        with (
            workflow_trace_scope(_AUTOPILOT),
            workflow_trace_scope(WorkflowTraceScope(user_id="owner-1")),
        ):
            attributes = build_phase_trace({"phase": "content"})

        assert attributes.metadata == {
            "project_id": "p-1",
            "phase": "content",
            "agent_name": "autopilot",
            "user_id": "owner-1",
            "content_type": "carousel",
        }
        assert attributes.user_id == "owner-1"
        assert attributes.tags == (
            "phase:content",
            "agent:autopilot",
            "content:carousel",
        )

    def test_explicit_metadata_wins_and_extra_keys_are_kept(self) -> None:
        with workflow_trace_scope(_AUTOPILOT):
            attributes = build_phase_trace({
                "phase": "draft",
                "content_type": "blog_post",
                "post_id": "post-9",
                "user_id": "",
            })

        assert attributes.metadata["content_type"] == "blog_post"
        assert attributes.metadata["post_id"] == "post-9"
        assert attributes.metadata["user_id"] == "unknown"
        assert attributes.tags[2] == "content:blog_post"

    def test_long_values_are_truncated_for_langfuse(self) -> None:
        attributes = build_phase_trace({"phase": "outline", "project_id": "x" * 500})

        assert len(attributes.metadata["project_id"]) == 200


class TestWorkflowTraceScope:
    def test_scope_resets_after_the_block(self) -> None:
        with workflow_trace_scope(_AUTOPILOT):
            assert current_trace_scope().agent_name == "autopilot"

        assert current_trace_scope() == WorkflowTraceScope()

    def test_empty_fields_inherit_the_outer_scope(self) -> None:
        with (
            workflow_trace_scope(_AUTOPILOT),
            workflow_trace_scope(WorkflowTraceScope(project_id="p-2")),
        ):
            scope = current_trace_scope()

        assert scope.project_id == "p-2"
        assert scope.agent_name == "autopilot"


class TestPhaseTrace:
    # Scenario: Tracing is a no-op without Langfuse
    def test_no_client_yields_without_a_trace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(langfuse_phase_trace, "get_langfuse_client", lambda: None)
        ran: list[bool] = []

        with phase_trace({"phase": "outline"}):
            ran.append(True)

        assert ran == [True]

    def test_span_trace_and_propagation_carry_the_attributes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        collector = install_trace_collector(monkeypatch)

        with workflow_trace_scope(_AUTOPILOT), phase_trace({"phase": "design"}):
            active = collector.current()

        assert active is not None
        assert active.name == "workflow_design"
        assert active.trace_name == "workflow_design"
        assert active.span_metadata == active.metadata
        assert active.tags == ["phase:design", "agent:autopilot", "content:carousel"]
        assert active.propagated == {
            "trace_name": "workflow_design",
            "user_id": None,
            "session_id": "p-1",
            "metadata": active.metadata,
            "tags": active.tags,
        }
        assert collector.current() is None
        assert collector.flushes == 1

    def test_flushes_when_the_phase_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        collector = install_trace_collector(monkeypatch)

        with pytest.raises(RuntimeError), phase_trace({"phase": "images"}):
            raise RuntimeError("provider down")

        assert collector.flushes == 1
        assert collector.current() is None

    def test_legacy_propagate_attributes_opens_the_same_trace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        collector = install_trace_collector(monkeypatch)

        with propagate_attributes(metadata={"phase": "research", "user_id": "u-1"}):
            active = collector.current()

        assert active is not None
        assert active.name == "workflow_research"
        assert active.user_id == "u-1"
        assert "phase:research" in active.tags
