"""Content phase node: the slide-copy gate (split from carousel_workflow_nodes).

AE-0405: the content ensure is a non-idempotent side effect before the review
interrupt (it may regenerate every slide with the LLM). LangGraph replays the
interrupted node on resume, so the artifacts of the pass the reviewer saw ride
the interrupt payload; the engine writes them to the checkpoint when the graph
parks and the replay reuses them instead of running the ensure again.
"""

from __future__ import annotations

from typing import cast

import structlog
from langchain_core.runnables import RunnableConfig

from rag_backend.agents.carousel_workflow_nodes import (
    SyncArtifactPhaseConfig,
    ensure_artifacts,
    run_sync_artifact_phase,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    INTERRUPT_TYPE_CONTENT_REVIEW,
    PHASE_CONTENT,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    WORKFLOW_ERROR_KEY,
)
from rag_backend.domain.constants.content_feedback import (
    LOG_CONTENT_REPLAY_REUSED,
    PAYLOAD_KEY_PARKED_ARTIFACTS,
    STATE_FIELD_CONTENT_ARTIFACTS_PARKED,
)
from rag_backend.domain.constants.workflow_state_fields import (
    STATE_FIELD_CONTENT_GATE_VALIDATION,
)

logger = structlog.get_logger()


def _content_review_payload(merged: dict[str, object]) -> dict[str, object]:
    """Content interrupt payload incl. the fail-closed gate report (AE-0309)."""
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
    """Content gate config; ``parked_updates`` ride the interrupt (AE-0405)."""
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
        # The node finished: the next content entry runs its ensure again.
        post_review={STATE_FIELD_CONTENT_ARTIFACTS_PARKED: False},
    )


def content_phase(
    state: CarouselWorkflowState,
    config: RunnableConfig | None = None,
) -> dict[str, object]:
    """Draft slide content and request human approval."""
    return run_sync_artifact_phase(state, config, _content_artifact_config())


async def _content_ensure_or_reuse(
    state: CarouselWorkflowState,
    config: RunnableConfig | None,
) -> dict[str, object]:
    """Run the content ensure, unless this is the replay of a parked review.

    AE-0405: LangGraph re-runs the interrupted node on resume. The engine wrote
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


async def content_phase_async(
    state: CarouselWorkflowState,
    config: RunnableConfig,
) -> dict[str, object]:
    merged = dict(state)
    artifact_updates = await _content_ensure_or_reuse(state, config)
    merged.update(artifact_updates)
    # AE-0330: decide on THIS run's artifact result, not on whatever
    # phase_status the checkpoint carried in. A failure here returns without
    # interrupting and the graph routes it to END (_ROUTE_FAILED).
    if artifact_updates.get("phase_status") == PHASE_STATUS_FAILED:
        # Name the phase that failed. ensure_artifacts only stamps
        # current_phase on its own copy, so without this the END state still
        # says "outline" and needs_gate_reopen checks outline_approved (True)
        # — a retry then resumes a finished graph and silently does nothing.
        merged["current_phase"] = PHASE_CONTENT
        return merged
    if merged.get("phase_status") == PHASE_STATUS_FAILED:
        # Stale failure from a previous run whose artifacts have now been
        # rebuilt successfully. Resume only flips the DB row to in_progress,
        # never the checkpoint, so without this the old flag re-triggered the
        # early return above on every retry — the second half of the live
        # 2026-09-14 loop, with all seven drafts already present.
        merged["phase_status"] = PHASE_STATUS_IN_PROGRESS
        merged[WORKFLOW_ERROR_KEY] = ""
    sync_result = run_sync_artifact_phase(
        cast(CarouselWorkflowState, merged),
        config,
        _content_artifact_config(artifact_updates),
    )
    return {**merged, **sync_result}


__all__ = ["content_phase", "content_phase_async"]
