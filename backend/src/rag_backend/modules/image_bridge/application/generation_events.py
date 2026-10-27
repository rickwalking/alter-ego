"""Safe generation-log observations for image bridge jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rag_backend.modules.generation_queue.events_public import (
    EVENT_IMAGE_JOB_FAILED,
    MESSAGE_IMAGE_JOB,
    OUTCOME_FAILED,
    GenerationEventInput,
    record_generation_event,
)
from rag_backend.modules.image_bridge.domain.models import ImageBridgeJob

_SAFE_ERROR_CODES = frozenset({
    "content_policy",
    "expired",
    "invalid_image",
    "job_missing",
    "malformed_callback",
    "no_image",
    "provider_error",
    "rate_limited",
    "timeout",
    "unknown_error",
    "webhook_failed",
})
_UNKNOWN_ERROR = "unknown_error"


def safe_image_error_code(error_code: str | None) -> str | None:
    """Keep known classifications and replace external/free-text codes."""
    if error_code is None:
        return None
    return error_code if error_code in _SAFE_ERROR_CODES else _UNKNOWN_ERROR


@dataclass(frozen=True, kw_only=True)
class ImageJobObservation:
    """The content-free fields of one image-job transition."""

    event_type: str
    job: ImageBridgeJob
    outcome: str
    occurred_at: datetime
    duration_ms: int | None = None
    error_code: str | None = None
    model: str | None = None


async def record_image_job(observation: ImageJobObservation) -> None:
    """Persist job diagnostics without prompt, token, path or image data."""
    job = observation.job
    details: dict[str, object] = {
        "image_job_id": str(job.id),
        "size": job.size,
        "job_status": job.status.value,
    }
    if observation.model is not None:
        details["model"] = observation.model
    await record_generation_event(
        GenerationEventInput(
            event_type=observation.event_type,
            outcome=observation.outcome,
            phase="images",
            occurred_at=observation.occurred_at,
            duration_ms=observation.duration_ms,
            error_code=safe_image_error_code(observation.error_code),
            message_code=MESSAGE_IMAGE_JOB,
            details=details,
        )
    )


async def record_terminal_image_job(
    job: ImageBridgeJob, error_code: str | None, now: datetime
) -> None:
    """Record a failed or expired job without its external error text."""
    duration_ms = max(0, round((now - job.created_at).total_seconds() * 1000))
    await record_image_job(
        ImageJobObservation(
            event_type=EVENT_IMAGE_JOB_FAILED,
            job=job,
            outcome=OUTCOME_FAILED,
            occurred_at=now,
            duration_ms=duration_ms,
            error_code=error_code,
        )
    )


__all__ = [
    "ImageJobObservation",
    "record_image_job",
    "record_terminal_image_job",
    "safe_image_error_code",
]
