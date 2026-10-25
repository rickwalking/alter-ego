"""Carousel workflow phase nodes and human-review helpers.

_SEND_BACK_RESET_APPROVED_FIELDS maps a send-back target to the approval flag reset when
a phase node honors the send-back, so the target phase re-gates instead of
auto-approving off a stale flag.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from rag_backend.agents.carousel_content_park import manual_fixes_park_updates
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
    CAROUSEL_WORKFLOW_PHASES,
    DESIGN_SEND_BACK_PHASES,
    EDITED_SLIDES_ALLOWED_PHASES,
    INTERRUPT_TYPE_CONTENT_REVIEW,
    INTERRUPT_TYPE_DESIGN_REVIEW,
    INTERRUPT_TYPE_FINAL_REVIEW,
    INTERRUPT_TYPE_IMAGE_REVIEW,
    INTERRUPT_TYPE_OUTLINE_REVIEW,
    INTERRUPT_TYPE_RESEARCH_REVIEW,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_RESEARCH,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_REVISE,
    SEND_BACK_TARGET_PHASE_KEY,
    STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY,
    STRUCTURED_FEEDBACK_KEY,
    STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
    WORKFLOW_ERROR_KEY,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.content_feedback import (
    LOG_CONTENT_REPLAY_REUSED,
    PAYLOAD_KEY_PARKED_ARTIFACTS,
    STATE_FIELD_CONTENT_ARTIFACTS_PARKED,
)
from rag_backend.domain.constants.langfuse_tracing import (
    TRACE_FIELD_PHASE,
    TRACE_FIELD_PROJECT_ID,
    TRACE_INPUT_TOPIC,
    TRACE_OUTPUT_UPDATED_KEYS,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_CONTENT_GATE_VALIDATION,
    STATE_FIELD_DESIGN_RECOVERY_HINT,
    STATE_FIELD_PRESENTATION_VALIDATION,
)
from rag_backend.infrastructure.monitoring_langfuse import phase_trace
from rag_backend.modules.presentation import (
    apply_localized_slide_edits_via_port,
)

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.phase_artifact_runner import (
        PhaseArtifactRunner,
    )

logger = structlog.get_logger()

_CONFIG_ARTIFACT_RUNNER = "artifact_runner"

_SEND_BACK_RESET_APPROVED_FIELDS: dict[str, str] = {
    PHASE_CONTENT: "content_approved",
}


@dataclass(frozen=True)
class SyncArtifactPhaseConfig:
    """Parameters for sync artifact phase nodes with human review gates.

    send_back_phases are the phases this node's revise may send the workflow back to.
    """

    phase: str
    interrupt_type: str
    payload_key: str
    approved_field: str
    message: str
    extra_payload: dict[str, object] | None = None
    payload_builder: object | None = None
    post_review: dict[str, object] | None = None
    send_back_phases: frozenset[str] = frozenset()


def artifact_runner_from_config(
    config: RunnableConfig | None,
) -> PhaseArtifactRunner | None:
    if config is None:
        return None
    configurable = config.get("configurable", {})
    runner = configurable.get(_CONFIG_ARTIFACT_RUNNER)
    if runner is None:
        return None
    return cast("PhaseArtifactRunner", runner)


def _edited_slide_updates(
    review: dict[str, object],
    state: CarouselWorkflowState | None,
    phase: str | None,
) -> dict[str, object]:
    """Apply reviewer slide edits to workflow state updates.

    Uniform semantics at every allowed phase (content, design, final_review):
    apply the edits to ``localized_slides``, re-run presentation validation,
    and store the fresh report.
    """
    if phase not in EDITED_SLIDES_ALLOWED_PHASES or state is None:
        return {}
    structured = review.get(STRUCTURED_FEEDBACK_KEY)
    if not isinstance(structured, dict):
        return {}
    edited = structured.get(STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY)
    if not isinstance(edited, list) or not edited:
        return {}
    edited_dicts = [slide for slide in edited if isinstance(slide, dict)]
    return apply_localized_slide_edits_via_port(state, edited_dicts)


def review_updates_from_response(
    review: dict[str, object],
    *,
    state: CarouselWorkflowState | None = None,
    phase: str | None = None,
) -> dict[str, object]:
    """Map a review response onto graph-state updates.

    Any revise or reject drops the publish approval in the graph state; otherwise
    get_state copies a stale approved_for_publish back to the DB on the resume sync and
    reopens a stale-publish window for the whole revision. This also covers a revise
    without a target from a held carousel, since a stale send-back target could still
    route it to an earlier phase. The later final_review re-approval restores
    approved_for_publish.
    """
    action = review.get("action")
    edit_updates = _edited_slide_updates(review, state, phase)
    if action == REVIEW_ACTION_APPROVE:
        return {**edit_updates, "phase_status": PHASE_STATUS_APPROVED}
    if action not in {REVIEW_ACTION_REVISE, REVIEW_ACTION_REJECT}:
        return {"phase_status": PHASE_STATUS_AWAITING_HUMAN}
    updates: dict[str, object] = {
        **edit_updates,
        "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        "workflow_status": CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
        "quality_passed": False,
    }
    structured = review.get(STRUCTURED_FEEDBACK_KEY)
    if isinstance(structured, dict):
        target = structured.get(STRUCTURED_FEEDBACK_TARGET_PHASE_KEY)
        if isinstance(target, str) and target in CAROUSEL_WORKFLOW_PHASES:
            updates[SEND_BACK_TARGET_PHASE_KEY] = target
            updates["current_phase"] = target
    return updates


def await_human_review(
    state: CarouselWorkflowState,
    phase: str,
    interrupt_type: str,
    payload: dict[str, object],
) -> dict[str, object]:
    """Pause workflow until a human reviewer responds."""
    review = interrupt({
        "type": interrupt_type,
        "phase": phase,
        "project_id": state.get("project_id"),
        **payload,
    })
    if not isinstance(review, dict):
        return {"phase_status": PHASE_STATUS_AWAITING_HUMAN}
    return review_updates_from_response(review, state=state, phase=phase)


async def ensure_artifacts(
    state: CarouselWorkflowState,
    config: RunnableConfig | None,
    phase: str,
) -> dict[str, object]:
    """Build the phase artifacts unless the state already holds them.

    Every phase LLM call runs inside the named, tagged phase trace.
    """
    runner = artifact_runner_from_config(config)
    if runner is None:
        return {}
    merged = dict(state)
    merged["current_phase"] = phase
    project_id = str(state.get("project_id", ""))
    trace_input = {
        TRACE_FIELD_PHASE: phase,
        TRACE_INPUT_TOPIC: state.get(TRACE_INPUT_TOPIC, ""),
    }
    with phase_trace(
        {TRACE_FIELD_PHASE: phase, TRACE_FIELD_PROJECT_ID: project_id},
        trace_input=trace_input,
    ) as trace:
        result = await runner.ensure_for_phase(cast(CarouselWorkflowState, merged))
        trace.set_output({
            TRACE_FIELD_PHASE: phase,
            TRACE_OUTPUT_UPDATED_KEYS: sorted(result),
        })
        return result


def brief_phase(_state: CarouselWorkflowState) -> dict[str, object]:
    """Validate brief and move to research."""
    return {
        "current_phase": PHASE_RESEARCH,
        "phase_status": PHASE_STATUS_IN_PROGRESS,
        "brief_approved": True,
    }


def research_phase(state: CarouselWorkflowState) -> dict[str, object]:
    """Run research then request human review."""
    findings = state.get("research_findings") or []
    review_update = await_human_review(
        state,
        PHASE_RESEARCH,
        INTERRUPT_TYPE_RESEARCH_REVIEW,
        {"findings": findings, "message": "Review research findings."},
    )
    approved = review_update.get("phase_status") == PHASE_STATUS_APPROVED
    return {
        **review_update,
        "research_approved": approved,
        "current_phase": PHASE_RESEARCH,
    }


def _sync_phase_send_back_target(
    review_update: dict[str, object],
    artifact: SyncArtifactPhaseConfig,
) -> str | None:
    """Return a send-back target this node honors, if the review carries one."""
    target = review_update.get(SEND_BACK_TARGET_PHASE_KEY)
    if isinstance(target, str) and target in artifact.send_back_phases:
        return target
    return None


def _sync_phase_result(
    review_update: dict[str, object],
    artifact: SyncArtifactPhaseConfig,
) -> dict[str, object]:
    """Merge the review response into the node result (send-back aware).

    On a send-back, current_phase stays the target from the review update (it is not
    clobbered back to this node's phase) and the target's approval flag is reset so it
    re-gates instead of skipping ahead on a stale approve. A consumed or stale target is
    then cleared so it cannot re-route a later cycle.
    """
    approved = review_update.get("phase_status") == PHASE_STATUS_APPROVED
    result: dict[str, object] = {**review_update, artifact.approved_field: approved}
    target = None if approved else _sync_phase_send_back_target(review_update, artifact)
    if target is not None:
        reset_field = _SEND_BACK_RESET_APPROVED_FIELDS.get(target)
        if reset_field is not None:
            result[reset_field] = False
        return result
    result["current_phase"] = artifact.phase
    if artifact.send_back_phases:
        result[SEND_BACK_TARGET_PHASE_KEY] = ""
    if artifact.post_review:
        result.update(artifact.post_review)
    return result


def _run_sync_artifact_phase(
    state: CarouselWorkflowState,
    _config: RunnableConfig | None,
    artifact: SyncArtifactPhaseConfig,
) -> dict[str, object]:
    merged = dict(state)
    if artifact.payload_builder is not None and callable(artifact.payload_builder):
        payload = artifact.payload_builder(merged)
    else:
        payload = {artifact.payload_key: merged.get(artifact.payload_key) or []}
    if artifact.extra_payload:
        payload.update(artifact.extra_payload)
    payload["message"] = artifact.message
    review_update = await_human_review(
        merged,
        artifact.phase,
        artifact.interrupt_type,
        payload,
    )
    return _sync_phase_result(review_update, artifact)


def outline_phase(
    state: CarouselWorkflowState,
    config: RunnableConfig | None = None,
) -> dict[str, object]:
    """Generate outline and request human approval."""
    return _run_sync_artifact_phase(
        state,
        config,
        SyncArtifactPhaseConfig(
            phase=PHASE_OUTLINE,
            interrupt_type=INTERRUPT_TYPE_OUTLINE_REVIEW,
            payload_key="outline",
            approved_field="outline_approved",
            message="Review and approve the outline.",
        ),
    )


def _content_review_payload(merged: dict[str, object]) -> dict[str, object]:
    """Content interrupt payload incl. the fail-closed gate report."""
    return {
        "slide_drafts": merged.get("slide_drafts") or [],
        "persona_scores": merged.get("persona_scores") or {},
        STATE_FIELD_CONTENT_GATE_VALIDATION: (
            merged.get(STATE_FIELD_CONTENT_GATE_VALIDATION) or {}
        ),
    }


def _content_artifact_config(
    parked_updates: dict[str, object] | None = None,
) -> SyncArtifactPhaseConfig:
    """Content gate config; ``parked_updates`` ride the interrupt.

    Once the node finishes, the next content entry runs its ensure again.
    """
    return SyncArtifactPhaseConfig(
        phase=PHASE_CONTENT,
        interrupt_type=INTERRUPT_TYPE_CONTENT_REVIEW,
        payload_key="slide_drafts",
        approved_field="content_approved",
        message="Review slide copy.",
        payload_builder=_content_review_payload,
        extra_payload=(
            {PAYLOAD_KEY_PARKED_ARTIFACTS: parked_updates} if parked_updates else None
        ),
        post_review={STATE_FIELD_CONTENT_ARTIFACTS_PARKED: False},
    )


def content_phase(
    state: CarouselWorkflowState,
    config: RunnableConfig | None = None,
) -> dict[str, object]:
    """Draft slide content and request human approval."""
    return _run_sync_artifact_phase(state, config, _content_artifact_config())


def _design_review_payload(merged: dict[str, object]) -> dict[str, object]:
    """Design interrupt payload incl. the fresh validation report.

    While the report blocks, the payload carries the client-displayable
    recovery hint: direct edits or a content send-back resolve violations —
    a plain revise alone does not modify content.
    """
    return {
        "design_applied": merged.get("design_applied", False),
        STATE_FIELD_PRESENTATION_VALIDATION: (
            merged.get(STATE_FIELD_PRESENTATION_VALIDATION) or {}
        ),
        STATE_FIELD_DESIGN_RECOVERY_HINT: str(
            merged.get(STATE_FIELD_DESIGN_RECOVERY_HINT) or ""
        ),
    }


def design_phase(
    state: CarouselWorkflowState,
    config: RunnableConfig | None = None,
) -> dict[str, object]:
    """Apply design and request human approval."""
    return _run_sync_artifact_phase(
        state,
        config,
        SyncArtifactPhaseConfig(
            phase=PHASE_DESIGN,
            interrupt_type=INTERRUPT_TYPE_DESIGN_REVIEW,
            payload_key="design_applied",
            approved_field="design_approved",
            message="Review design.",
            payload_builder=_design_review_payload,
            post_review={"design_applied": True},
            send_back_phases=DESIGN_SEND_BACK_PHASES,
        ),
    )


def images_phase(
    state: CarouselWorkflowState,
    config: RunnableConfig | None = None,
) -> dict[str, object]:
    """Generate images and request human approval."""
    return _run_sync_artifact_phase(
        state,
        config,
        SyncArtifactPhaseConfig(
            phase=PHASE_IMAGES,
            interrupt_type=INTERRUPT_TYPE_IMAGE_REVIEW,
            payload_key="image_assets",
            approved_field="images_approved",
            message="Review generated images.",
            payload_builder=lambda merged: {
                "image_assets": merged.get("image_assets") or [],
            },
        ),
    )


async def outline_phase_async(
    state: CarouselWorkflowState,
    config: RunnableConfig,
) -> dict[str, object]:
    merged = dict(state)
    merged.update(await ensure_artifacts(state, config, PHASE_OUTLINE))
    sync_result = outline_phase(cast(CarouselWorkflowState, merged), config)
    return {**merged, **sync_result}


async def _content_ensure_or_reuse(
    state: CarouselWorkflowState,
    config: RunnableConfig | None,
) -> dict[str, object]:
    """Run the content ensure, unless this is the replay of a parked review.

    LangGraph re-runs the interrupted node on resume. The engine wrote
    the artifacts the reviewer saw to the checkpoint when the graph parked, so
    the replay reuses them: no second regeneration with the same notes, no
    LLM call, and the reviewed (or hand-edited) copy is what gets committed.
    """
    if state.get(STATE_FIELD_CONTENT_ARTIFACTS_PARKED) is True:
        logger.info(
            LOG_CONTENT_REPLAY_REUSED, project_id=str(state.get("project_id", ""))
        )
        return {}
    return await ensure_artifacts(state, config, PHASE_CONTENT)


async def _rescore_after_manual_fixes(
    state: CarouselWorkflowState,
    config: RunnableConfig | None,
    park: dict[str, object],
) -> dict[str, object]:
    """Persona scores of the hand-edited copy, in the node return that is persisted.

    An edits-only revise applies the edits after ``interrupt()`` returns; this
    node then returns (the graph routes back to content), so scoring here stores
    the new scores in the checkpoint. Scoring on the replay put them only on the
    next interrupt payload, which LangGraph never persists, so approve kept
    refusing the pre-edit score. Unedited slides keep their scores (fingerprints).
    """
    if not park:
        return {}
    runner = artifact_runner_from_config(config)
    return {} if runner is None else await runner.rescore_edited_content(state)


async def content_phase_async(
    state: CarouselWorkflowState,
    config: RunnableConfig,
) -> dict[str, object]:
    """Run the content phase: build the drafts, then interrupt for review.

    The decision uses this run's artifact result, not the phase_status the checkpoint
    carried in. A failure returns without interrupting and the graph routes it to END;
    current_phase is set to content because ensure_artifacts only stamps its own copy,
    and an END state still saying outline would make needs_gate_reopen check
    outline_approved and turn a retry into a silent no-op. A stale failure from a
    previous run whose artifacts were since rebuilt is reset to in_progress: resume only
    flips the DB row, never the checkpoint, so the old flag would re-trigger the early
    return on every retry.
    """
    merged = dict(state)
    artifact_updates = await _content_ensure_or_reuse(state, config)
    merged.update(artifact_updates)
    if artifact_updates.get("phase_status") == PHASE_STATUS_FAILED:
        merged["current_phase"] = PHASE_CONTENT
        return merged
    if merged.get("phase_status") == PHASE_STATUS_FAILED:
        merged["phase_status"] = PHASE_STATUS_IN_PROGRESS
        merged[WORKFLOW_ERROR_KEY] = ""
    sync_result = _run_sync_artifact_phase(
        cast(CarouselWorkflowState, merged),
        config,
        _content_artifact_config(artifact_updates),
    )
    park = manual_fixes_park_updates(sync_result, merged)
    edited = cast(CarouselWorkflowState, {**merged, **sync_result})
    rescored = await _rescore_after_manual_fixes(edited, config, park)
    return {**merged, **sync_result, **park, **rescored}


async def design_phase_async(
    state: CarouselWorkflowState,
    config: RunnableConfig,
) -> dict[str, object]:
    merged = dict(state)
    merged.update(await ensure_artifacts(state, config, PHASE_DESIGN))
    sync_result = design_phase(cast(CarouselWorkflowState, merged), config)
    return {**merged, **sync_result}


async def images_phase_async(
    state: CarouselWorkflowState,
    config: RunnableConfig,
) -> dict[str, object]:
    merged = dict(state)
    merged.update(await ensure_artifacts(state, config, PHASE_IMAGES))
    sync_result = images_phase(cast(CarouselWorkflowState, merged), config)
    return {**merged, **sync_result}


def final_review_phase(state: CarouselWorkflowState) -> dict[str, object]:
    """Final quality gate before publish.

    On a send-back the review update already carries current_phase=<target>; it must not
    be clobbered back to final_review, or the committed checkpoint reports final_review
    and the edited slides are rejected by the phase check. current_phase is pinned to
    final_review only when there is no valid send-back target, and the membership guard
    keeps a stale or corrupted target out of current_phase. On approval, a send-back
    target consumed in a prior cycle is cleared so it cannot route a later resume from
    the approved_hold node.
    """
    review_update = await_human_review(
        state,
        PHASE_FINAL_REVIEW,
        INTERRUPT_TYPE_FINAL_REVIEW,
        {
            "rubric_scores": state.get("rubric_scores") or {},
            "message": "Final review before publish.",
        },
    )
    approved = review_update.get("phase_status") == PHASE_STATUS_APPROVED
    send_back_target = review_update.get(SEND_BACK_TARGET_PHASE_KEY)
    has_send_back = (
        isinstance(send_back_target, str)
        and send_back_target in CAROUSEL_WORKFLOW_PHASES
    )
    result: dict[str, object] = {
        **review_update,
        "quality_passed": approved,
        "workflow_status": (
            WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
            if approved
            else state.get("workflow_status", "")
        ),
        "status": "draft",
    }
    if not has_send_back:
        result["current_phase"] = PHASE_FINAL_REVIEW
    if approved:
        result[SEND_BACK_TARGET_PHASE_KEY] = ""
    return result


def approved_hold_phase(state: CarouselWorkflowState) -> dict[str, object]:
    """Hold an approved carousel at an interrupt so it stays resumable.

    After final-review approval the graph parks here instead of reaching END,
    keeping ``quality_passed`` / ``workflow_status=approved_for_publish`` intact.
    A human send-back resume (revise + ``structured_feedback.target_phase``)
    routes the workflow back to the targeted phase to regenerate it; any other
    resume finalizes the run. While parked here the checkpoint still reports
    ``current_phase=final_review`` / ``phase_status=approved`` (see
    ``CarouselWorkflowEngine.get_state``), so the carousel remains publishable.
    """
    return await_human_review(
        state,
        PHASE_FINAL_REVIEW,
        INTERRUPT_TYPE_FINAL_REVIEW,
        {
            "rubric_scores": state.get("rubric_scores") or {},
            "message": "Approved for publish — awaiting publish or revision.",
        },
    )


__all__ = [
    "_CONFIG_ARTIFACT_RUNNER",
    "approved_hold_phase",
    "artifact_runner_from_config",
    "brief_phase",
    "content_phase",
    "content_phase_async",
    "design_phase_async",
    "final_review_phase",
    "images_phase_async",
    "outline_phase_async",
    "research_phase",
]
