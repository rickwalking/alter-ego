"""Each graph phase builds its artifacts inside the phase trace (AE-0390).

Gherkin: tests/features/workflow_tracing_and_heartbeat.feature
  Scenario Outline: A resumed phase runs its LLM calls in a named, tagged trace

``ensure_artifacts`` is the one seam every phase LLM call goes through
(outline, content incl. persona scoring and distribution, design, images).
The end-to-end resume paths are in tests/integration/test_phase_traces_ae0390.py.
"""

from __future__ import annotations

import pytest
from langchain_core.runnables import RunnableConfig

from rag_backend.agents.carousel_workflow_nodes import (
    _CONFIG_ARTIFACT_RUNNER,
    ensure_artifacts,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.infrastructure.langfuse_phase_trace import (
    WorkflowTraceScope,
    workflow_trace_scope,
)
from tests.langfuse_trace_fakes import (
    RecordedTrace,
    TraceCollector,
    install_trace_collector,
)


class _Runner:
    """Stands in for PhaseArtifactRunner: the 'LLM call' notes its trace."""

    def __init__(self, collector: TraceCollector) -> None:
        self._collector = collector
        self.seen: list[RecordedTrace | None] = []

    async def ensure_for_phase(self, state: CarouselWorkflowState) -> dict[str, object]:
        self.seen.append(self._collector.current())
        return {"phase_built": state.get("current_phase")}


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["outline", "content", "design", "images"])
async def test_phase_artifacts_run_in_the_phase_trace(
    phase: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    collector = install_trace_collector(monkeypatch)
    runner = _Runner(collector)
    config: RunnableConfig = {"configurable": {_CONFIG_ARTIFACT_RUNNER: runner}}
    state: CarouselWorkflowState = {"project_id": "p-1"}

    with workflow_trace_scope(
        WorkflowTraceScope(user_id="owner-1", agent_name="autopilot")
    ):
        updates = await ensure_artifacts(state, config, phase)

    assert updates == {"phase_built": phase}
    trace = runner.seen[0]
    assert trace is not None
    assert trace.name == f"workflow_{phase}"
    assert trace.metadata == {
        "project_id": "p-1",
        "phase": phase,
        "agent_name": "autopilot",
        "user_id": "owner-1",
        "content_type": "carousel",
    }
    assert trace.tags == [f"phase:{phase}", "agent:autopilot", "content:carousel"]
    assert collector.current() is None


@pytest.mark.asyncio
async def test_no_runner_opens_no_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = install_trace_collector(monkeypatch)

    updates = await ensure_artifacts({"project_id": "p-1"}, None, "outline")

    assert updates == {}
    assert collector.traces == []
