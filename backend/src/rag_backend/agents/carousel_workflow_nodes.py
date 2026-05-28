"""Carousel workflow phase nodes and human-review helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    CAROUSEL_WORKFLOW_PHASES,
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
    STRUCTURED_FEEDBACK_KEY,
    STRUCTURED_FEEDBACK_TARGET_PHASE_KEY,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.phase_artifact_runner import (
        PhaseArtifactRunner,
    )

_CONFIG_ARTIFACT_RUNNER = "artifact_runner"


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


def review_updates_from_response(review: dict[str, object]) -> dict[str, object]:
    action = review.get("action")
    if action == REVIEW_ACTION_APPROVE:
        return {"phase_status": PHASE_STATUS_APPROVED}
    if action not in {REVIEW_ACTION_REVISE, REVIEW_ACTION_REJECT}:
        return {"phase_status": PHASE_STATUS_AWAITING_HUMAN}
    updates: dict[str, object] = {"phase_status": PHASE_STATUS_AWAITING_HUMAN}
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
    return review_updates_from_response(review)


async def ensure_artifacts(
    state: CarouselWorkflowState,
    config: RunnableConfig | None,
    phase: str,
) -> dict[str, object]:
    runner = artifact_runner_from_config(config)
    if runner is None:
        return {}
    merged = dict(state)
    merged["current_phase"] = phase
    return await runner.ensure_for_phase(cast(CarouselWorkflowState, merged))


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


def _run_sync_artifact_phase(
    state: CarouselWorkflowState,
    config: RunnableConfig | None,
    *,
    phase: str,
    interrupt_type: str,
    payload_key: str,
    approved_field: str,
    message: str,
    extra_payload: dict[str, object] | None = None,
    payload_builder: object | None = None,
    post_review: dict[str, object] | None = None,
) -> dict[str, object]:
    """Sync wrapper: artifact generation runs via engine pre-node hook."""
    merged = dict(state)
    if payload_builder is not None and callable(payload_builder):
        payload = payload_builder(merged)
    else:
        payload = {payload_key: merged.get(payload_key) or []}
    if extra_payload:
        payload.update(extra_payload)
    payload["message"] = message
    review_update = await_human_review(merged, phase, interrupt_type, payload)
    approved = review_update.get("phase_status") == PHASE_STATUS_APPROVED
    result: dict[str, object] = {
        **review_update,
        approved_field: approved,
        "current_phase": phase,
    }
    if post_review:
        result.update(post_review)
    return result


def outline_phase(
    state: CarouselWorkflowState,
    config: RunnableConfig | None = None,
) -> dict[str, object]:
    """Generate outline and request human approval."""
    return _run_sync_artifact_phase(
        state,
        config,
        phase=PHASE_OUTLINE,
        interrupt_type=INTERRUPT_TYPE_OUTLINE_REVIEW,
        payload_key="outline",
        approved_field="outline_approved",
        message="Review and approve the outline.",
    )


def content_phase(
    state: CarouselWorkflowState,
    config: RunnableConfig | None = None,
) -> dict[str, object]:
    """Draft slide content and request human approval."""
    return _run_sync_artifact_phase(
        state,
        config,
        phase=PHASE_CONTENT,
        interrupt_type=INTERRUPT_TYPE_CONTENT_REVIEW,
        payload_key="slide_drafts",
        approved_field="content_approved",
        message="Review slide copy.",
        extra_payload={
            "persona_scores": state.get("persona_scores") or {},
        },
    )


def design_phase(
    state: CarouselWorkflowState,
    config: RunnableConfig | None = None,
) -> dict[str, object]:
    """Apply design and request human approval."""
    return _run_sync_artifact_phase(
        state,
        config,
        phase=PHASE_DESIGN,
        interrupt_type=INTERRUPT_TYPE_DESIGN_REVIEW,
        payload_key="design_applied",
        approved_field="design_approved",
        message="Review design.",
        payload_builder=lambda merged: {
            "design_applied": merged.get("design_applied", False),
        },
        post_review={"design_applied": True},
    )


def images_phase(
    state: CarouselWorkflowState,
    config: RunnableConfig | None = None,
) -> dict[str, object]:
    """Generate images and request human approval."""
    return _run_sync_artifact_phase(
        state,
        config,
        phase=PHASE_IMAGES,
        interrupt_type=INTERRUPT_TYPE_IMAGE_REVIEW,
        payload_key="image_assets",
        approved_field="images_approved",
        message="Review generated images.",
        payload_builder=lambda merged: {
            "image_assets": merged.get("image_assets") or [],
        },
    )


async def outline_phase_async(
    state: CarouselWorkflowState,
    config: RunnableConfig,
) -> dict[str, object]:
    merged = dict(state)
    merged.update(await ensure_artifacts(state, config, PHASE_OUTLINE))
    sync_result = outline_phase(cast(CarouselWorkflowState, merged), config)
    return {**merged, **sync_result}


async def content_phase_async(
    state: CarouselWorkflowState,
    config: RunnableConfig,
) -> dict[str, object]:
    merged = dict(state)
    merged.update(await ensure_artifacts(state, config, PHASE_CONTENT))
    if merged.get("phase_status") == PHASE_STATUS_FAILED:
        return merged
    sync_result = content_phase(cast(CarouselWorkflowState, merged), config)
    return {**merged, **sync_result}


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
    """Final quality gate before publish."""
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
    return {
        **review_update,
        "quality_passed": approved,
        "current_phase": PHASE_FINAL_REVIEW,
        "workflow_status": (
            WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
            if approved
            else state.get("workflow_status", "")
        ),
        "status": "draft",
    }


__all__ = [
    "_CONFIG_ARTIFACT_RUNNER",
    "artifact_runner_from_config",
    "brief_phase",
    "content_phase_async",
    "design_phase_async",
    "final_review_phase",
    "images_phase_async",
    "outline_phase_async",
    "research_phase",
]
