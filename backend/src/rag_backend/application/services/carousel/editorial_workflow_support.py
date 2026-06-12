"""SSE formatting and feedback persistence helpers for editorial workflow."""

from __future__ import annotations

from rag_backend.application.services.carousel.editorial_workflow_feedback import (
    persist_phase_feedback,
    read_checkpoint_phase,
)
from rag_backend.application.services.carousel.editorial_workflow_sse_build import (
    EventParams,
    build_artifact_event,
    build_error_event,
    build_phase_change_event,
    build_progress_event,
    build_review_gate_payload,
    build_review_required_event,
    build_workflow_event,
    resolve_background_resume_sse_error_message,
    resolve_workflow_sse_error_message,
)
from rag_backend.application.services.carousel.editorial_workflow_sse_constants import (
    SSE_EVENT_ARTIFACT,
    SSE_EVENT_ERROR,
    SSE_EVENT_KEEPALIVE,
    SSE_EVENT_PHASE_CHANGE,
    SSE_EVENT_PROGRESS,
    SSE_EVENT_REVIEW_REQUIRED,
    SSE_PAYLOAD_FIELD_EVENT,
    SSE_PAYLOAD_FIELD_GATE,
    SSE_PAYLOAD_FIELD_MESSAGE,
    SSE_PAYLOAD_FIELD_RECOVERABLE,
    WORKFLOW_ARTIFACT_UPDATE_FIELD_MAP,
    WORKFLOW_SSE_KEEPALIVE_SECONDS,
    WORKFLOW_SSE_MAX_SUBSCRIBERS_PER_PROJECT,
)
from rag_backend.application.services.carousel.editorial_workflow_sse_format import (
    format_sse_event,
)
from rag_backend.application.services.carousel.editorial_workflow_sse_publish import (
    PublishParams,
    publish_workflow_artifact,
    publish_workflow_artifacts_from_updates,
    publish_workflow_error,
    publish_workflow_phase_change,
    publish_workflow_progress,
    publish_workflow_review_required,
    publish_workflow_sse_updates,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    EditorialWorkflowStartInput,
    PhaseFeedbackPersistParams,
    ResumeWorkflowInput,
    ReviewEventEmitContext,
)

__all__ = [
    "SSE_EVENT_ARTIFACT",
    "SSE_EVENT_ERROR",
    "SSE_EVENT_KEEPALIVE",
    "SSE_EVENT_PHASE_CHANGE",
    "SSE_EVENT_PROGRESS",
    "SSE_EVENT_REVIEW_REQUIRED",
    "SSE_PAYLOAD_FIELD_EVENT",
    "SSE_PAYLOAD_FIELD_GATE",
    "SSE_PAYLOAD_FIELD_MESSAGE",
    "SSE_PAYLOAD_FIELD_RECOVERABLE",
    "WORKFLOW_ARTIFACT_UPDATE_FIELD_MAP",
    "WORKFLOW_SSE_KEEPALIVE_SECONDS",
    "WORKFLOW_SSE_MAX_SUBSCRIBERS_PER_PROJECT",
    "EditorialWorkflowStartInput",
    "EventParams",
    "PhaseFeedbackPersistParams",
    "PublishParams",
    "ResumeWorkflowInput",
    "ReviewEventEmitContext",
    "build_artifact_event",
    "build_error_event",
    "build_phase_change_event",
    "build_progress_event",
    "build_review_gate_payload",
    "build_review_required_event",
    "build_workflow_event",
    "format_sse_event",
    "persist_phase_feedback",
    "publish_workflow_artifact",
    "publish_workflow_artifacts_from_updates",
    "publish_workflow_error",
    "publish_workflow_phase_change",
    "publish_workflow_progress",
    "publish_workflow_review_required",
    "publish_workflow_sse_updates",
    "read_checkpoint_phase",
    "resolve_background_resume_sse_error_message",
    "resolve_workflow_sse_error_message",
]
