"""Carousel workflow engine runtime."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from langgraph.types import Command

from rag_backend.agents.carousel_workflow_graph import (
    build_carousel_workflow_graph,
    needs_gate_reopen,
)
from rag_backend.agents.carousel_workflow_nodes import _CONFIG_ARTIFACT_RUNNER
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
    get_initial_carousel_state,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_AWAITING_HUMAN

_REVIEW_INTERRUPT_KEYS = (
    "outline",
    "slide_drafts",
    "image_assets",
    "design_applied",
    "persona_scores",
    "rubric_scores",
)

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.phase_artifact_runner import (
        PhaseArtifactRunner,
    )


class CarouselWorkflowEngine:
    """Runs the editorial carousel workflow with LangGraph interrupts."""

    def __init__(
        self,
        checkpointer: object | None = None,
        artifact_runner: PhaseArtifactRunner | None = None,
    ) -> None:
        graph = build_carousel_workflow_graph()
        self._app = graph.compile(checkpointer=checkpointer)
        self._artifact_runner = artifact_runner

    def set_artifact_runner(self, artifact_runner: PhaseArtifactRunner | None) -> None:
        """Scope artifact generation to the current resume/request context."""
        self._artifact_runner = artifact_runner

    def _run_config(self, project_id: str) -> dict[str, object]:
        configurable: dict[str, object] = {"thread_id": project_id}
        if self._artifact_runner is not None:
            configurable[_CONFIG_ARTIFACT_RUNNER] = self._artifact_runner
        return {"configurable": configurable}

    @staticmethod
    def _iter_interrupt_values(snapshot: object) -> list[dict[str, object]]:
        payloads: list[dict[str, object]] = []
        for interrupt in getattr(snapshot, "interrupts", ()) or ():
            value = getattr(interrupt, "value", None)
            if isinstance(value, dict):
                payloads.append(value)
        for task in getattr(snapshot, "tasks", ()) or ():
            for interrupt in getattr(task, "interrupts", ()) or ():
                value = getattr(interrupt, "value", None)
                if isinstance(value, dict):
                    payloads.append(value)
        return payloads

    @classmethod
    def _merge_interrupt_review_payload(
        cls,
        state: CarouselWorkflowState,
        snapshot: object,
    ) -> None:
        """Expose gate review artifacts stored on pending interrupts."""
        for payload in cls._iter_interrupt_values(snapshot):
            findings = payload.get("findings")
            if (
                isinstance(findings, list)
                and findings
                and not state.get("research_findings")
            ):
                state["research_findings"] = findings
            for key in _REVIEW_INTERRUPT_KEYS:
                value = payload.get(key)
                if value is None:
                    continue
                if isinstance(value, (list, dict)) and not value:
                    continue
                if not state.get(key):
                    state[key] = value

    async def start(
        self,
        project_id: str,
        brief: dict[str, object] | None = None,
        **state_overrides: object,
    ) -> CarouselWorkflowState:
        """Start a new workflow run."""
        initial = get_initial_carousel_state(project_id, brief)
        initial.update(state_overrides)
        result = await self._app.ainvoke(initial, config=self._run_config(project_id))
        return cast(CarouselWorkflowState, result)

    async def resume(
        self,
        project_id: str,
        human_input: dict[str, object] | None = None,
    ) -> CarouselWorkflowState:
        """Resume a paused workflow after human review."""
        config = self._run_config(project_id)
        payload = human_input or {}
        snapshot = await self._app.aget_state(config)
        if snapshot is not None and needs_gate_reopen(snapshot):
            phase = str((snapshot.values or {}).get("current_phase", ""))
            result = await self._app.ainvoke(
                Command(goto=phase, resume=payload),
                config=config,
            )
            return cast(CarouselWorkflowState, result)
        result = await self._app.ainvoke(
            Command(resume=payload),
            config=config,
        )
        return cast(CarouselWorkflowState, result)

    async def update_state(
        self,
        project_id: str,
        values: dict[str, object],
    ) -> None:
        """Patch workflow state before resuming from an interrupt."""
        await self._app.aupdate_state(self._run_config(project_id), values)

    async def get_state(self, project_id: str) -> CarouselWorkflowState | None:
        """Load persisted workflow state from checkpointer (WF-002)."""
        config = self._run_config(project_id)
        snapshot = await self._app.aget_state(config)
        if snapshot is None or snapshot.values is None:
            return None
        values = snapshot.values
        if not isinstance(values, dict):
            return None
        state = cast(CarouselWorkflowState, dict(values))
        pending_interrupts = getattr(snapshot, "interrupts", ()) or ()
        pending_tasks = getattr(snapshot, "tasks", ()) or ()
        has_task_interrupt = any(
            getattr(task, "interrupts", ()) for task in pending_tasks
        )
        pending_next = getattr(snapshot, "next", ()) or ()
        if pending_next:
            state["current_phase"] = str(pending_next[0])
        elif pending_tasks:
            task_name = str(getattr(pending_tasks[0], "name", ""))
            if task_name:
                state["current_phase"] = task_name
        if pending_interrupts or has_task_interrupt or pending_next:
            state["phase_status"] = PHASE_STATUS_AWAITING_HUMAN
        self._merge_interrupt_review_payload(state, snapshot)
        return state


__all__ = ["CarouselWorkflowEngine"]
