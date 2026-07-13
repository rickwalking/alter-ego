"""Carousel workflow engine runtime."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from langgraph.types import Command

from rag_backend.agents.carousel_workflow_graph import (
    build_carousel_workflow_graph,
    needs_gate_reopen,
)
from rag_backend.agents.carousel_workflow_nodes import _CONFIG_ARTIFACT_RUNNER
from rag_backend.agents.harness.interrupts import iter_interrupt_values
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
    get_initial_carousel_state,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_APPROVED_HOLD,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_CONTENT_GATE_VALIDATION,
)
from rag_backend.domain.models.carousel_run import ensure_checkpoint_commit_allowed

_REVIEW_INTERRUPT_KEYS = (
    "outline",
    "slide_drafts",
    "image_assets",
    "design_applied",
    "persona_scores",
    "rubric_scores",
    # AE-0309: fail-closed content-gate report carried on the content interrupt.
    STATE_FIELD_CONTENT_GATE_VALIDATION,
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
    def _merge_interrupt_review_payload(
        state: CarouselWorkflowState,
        snapshot: object,
    ) -> None:
        """Expose gate review artifacts stored on pending interrupts.

        Carousel-coupled (knows ``CarouselWorkflowState``), so it stays in the
        engine; the generic snapshot scan is the harness ``iter_interrupt_values``.
        """
        for payload in iter_interrupt_values(snapshot):
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
        # AE-0315 layer (b): fence node-return application/checkpoint commits
        # against a reaped (stale-epoch) run before invoking the graph.
        await ensure_checkpoint_commit_allowed(project_id)
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
        # AE-0315 layer (b): a zombie run must not re-enter the graph and
        # commit checkpoints after its epoch was fenced by the reaper.
        await ensure_checkpoint_commit_allowed(project_id)
        config = self._run_config(project_id)
        payload = human_input or {}
        snapshot = await self._app.aget_state(config)
        # Corrupted-checkpoint recovery: when aupdate_state() was called
        # without as_node the pending interrupts may have been cleared while
        # the checkpoint still shows pending_next and in_progress phase_status.
        # Use Command(resume=payload) instead of ainvoke(None) to deliver the
        # human input directly.
        if snapshot is not None:
            pending_next = getattr(snapshot, "next", ()) or ()
            pending_interrupts = getattr(snapshot, "interrupts", ()) or ()
            has_task_interrupt = any(
                getattr(task, "interrupts", ())
                for task in (getattr(snapshot, "tasks", ()) or ())
            )
            phase_status = str((snapshot.values or {}).get("phase_status", ""))
            if (
                pending_next
                and not pending_interrupts
                and not has_task_interrupt
                and phase_status == PHASE_STATUS_IN_PROGRESS
            ):
                result = await self._app.ainvoke(
                    Command(resume=payload),
                    config=config,
                )
                return cast(CarouselWorkflowState, result)
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
        as_node: str | None = None,
    ) -> None:
        """Patch workflow state before resuming from an interrupt.

        When ``as_node`` is not provided and a pending interrupt exists, the
        first node name from the checkpoint ``snapshot.next`` is used as the
        default, preserving the pending interrupt context.
        """
        # AE-0315 layer (b): direct checkpoint patches are fenced too.
        await ensure_checkpoint_commit_allowed(project_id)
        config = self._run_config(project_id)
        if as_node is None:
            snapshot = await self._app.aget_state(config)
            if snapshot is not None:
                pending_next = getattr(snapshot, "next", ()) or ()
                if pending_next:
                    as_node = str(pending_next[0])
        await self._app.aupdate_state(config, values, as_node=as_node)

    async def patch_parked_checkpoint(
        self,
        project_id: str,
        values: dict[str, object],
    ) -> bool:
        """Patch a parked/held checkpoint WITHOUT advancing the node (AE-0314).

        The completed-project slide edit converges the checkpoint (source-of-
        truth option (a)) on an approved-hold thread. Writes with
        ``as_node=None`` so the pending park (``snapshot.next``) is preserved:
        inferring ``as_node`` from ``snapshot.next[0]`` would treat the
        ``approved_hold`` node as complete and advance it to END, losing
        resumability (the documented ``as_node`` footgun). Returns ``True`` when
        a parked checkpoint existed and was patched; ``False`` for END-state or
        absent threads (the legacy projection-only fallback).
        """
        await ensure_checkpoint_commit_allowed(project_id)
        config = self._run_config(project_id)
        snapshot = await self._app.aget_state(config)
        pending_next = (getattr(snapshot, "next", ()) or ()) if snapshot else ()
        if not pending_next:
            return False
        await self._app.aupdate_state(config, values, as_node=None)
        return True

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
        next_phase = (
            str(pending_next[0])
            if pending_next
            else str(getattr(pending_tasks[0], "name", ""))
            if pending_tasks
            else ""
        )
        # AE-0288: while parked at the internal approved_hold node the graph has a
        # pending interrupt, but the carousel is approved/publishable — it must NOT
        # surface as current_phase="approved_hold" or phase_status="awaiting_human".
        # Keep the stored final_review/approved values the final_review node wrote.
        held_at_approval = next_phase == PHASE_APPROVED_HOLD
        if next_phase and not held_at_approval:
            state["current_phase"] = next_phase
        if (pending_interrupts or has_task_interrupt) and not held_at_approval:
            state["phase_status"] = PHASE_STATUS_AWAITING_HUMAN
        self._merge_interrupt_review_payload(state, snapshot)
        return state


__all__ = ["CarouselWorkflowEngine"]
