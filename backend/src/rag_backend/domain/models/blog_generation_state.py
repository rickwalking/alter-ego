"""Pure transitions of ``ai_generation_metadata.generation`` (AE-0425, ADR-0025).

The run state of a generated post: ``{status, kind, started_at, heartbeat_at,
finished_at, lease_id, attempt, errors, recoverable, request, warnings,
image_count}``. Every function returns a **new** metadata dict (the other
metadata keys are preserved); the database adapter and the reaper persist them
behind the lease fence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from rag_backend.domain.constants.blog_document import (
    GENERATION_KEY,
    GENERATION_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.blog_generation import (
    ERR_GENERATION_INTERRUPTED,
    ERROR_KEY_AT,
    ERROR_KEY_CODE,
    ERROR_KEY_REASON,
    GEN_KEY_ATTEMPT,
    GEN_KEY_ERRORS,
    GEN_KEY_FINISHED_AT,
    GEN_KEY_HEARTBEAT_AT,
    GEN_KEY_IMAGE_COUNT,
    GEN_KEY_IMAGE_SLOTS,
    GEN_KEY_IMAGE_SPEND_USD,
    GEN_KEY_KIND,
    GEN_KEY_LEASE_ID,
    GEN_KEY_MODE,
    GEN_KEY_RECOVERABLE,
    GEN_KEY_REQUEST,
    GEN_KEY_STARTED_AT,
    GEN_KEY_STATUS,
    GEN_KEY_WARNINGS,
    GENERATION_STATUS_FAILED,
    METADATA_KEY_VOICE_SCORE,
)
from rag_backend.domain.models.blog_generation import GenerationOutcome


@dataclass(frozen=True)
class GenerationStart:
    """A new attempt: who/what started it and its fresh lease."""

    kind: str
    lease_id: str
    now: str
    request: dict[str, object]
    warnings: tuple[str, ...] = ()
    image_slots: int = 0
    # "" = the full run (writer + gate + images); ``images_only`` = a retry
    # that only fills the empty image slots of an existing article.
    mode: str = ""


def generation_of(metadata: object) -> dict[str, object]:
    """The ``generation`` dict of a metadata blob (empty when absent)."""
    if not isinstance(metadata, dict):
        return {}
    generation = metadata.get(GENERATION_KEY)
    return dict(generation) if isinstance(generation, dict) else {}


def lease_of(metadata: object) -> str | None:
    """The current ``generation.lease_id`` (``None`` when there is no live lease)."""
    lease = generation_of(metadata).get(GEN_KEY_LEASE_ID)
    return lease if isinstance(lease, str) and lease else None


def status_of(metadata: object) -> str | None:
    """The current ``generation.status``."""
    status = generation_of(metadata).get(GEN_KEY_STATUS)
    return status if isinstance(status, str) else None


def image_spend_of(metadata: object) -> float:
    """What every attempt so far spent on images for this post (USD)."""
    spend = generation_of(metadata).get(GEN_KEY_IMAGE_SPEND_USD)
    return float(spend) if isinstance(spend, int | float) else 0.0


def _attempt(metadata: object) -> int:
    attempt = generation_of(metadata).get(GEN_KEY_ATTEMPT)
    return attempt if isinstance(attempt, int) else 0


def _with_generation(
    metadata: object, generation: dict[str, object]
) -> dict[str, object]:
    base = dict(metadata) if isinstance(metadata, dict) else {}
    return {**base, GENERATION_KEY: generation}


def started(metadata: object, start: GenerationStart) -> dict[str, object]:
    """A new in-progress attempt (attempt + 1, fresh lease, errors cleared)."""
    return _with_generation(
        metadata,
        {
            GEN_KEY_STATUS: GENERATION_STATUS_IN_PROGRESS,
            GEN_KEY_KIND: start.kind,
            GEN_KEY_STARTED_AT: start.now,
            GEN_KEY_HEARTBEAT_AT: start.now,
            GEN_KEY_FINISHED_AT: None,
            GEN_KEY_LEASE_ID: start.lease_id,
            GEN_KEY_ATTEMPT: _attempt(metadata) + 1,
            GEN_KEY_ERRORS: [],
            GEN_KEY_RECOVERABLE: False,
            GEN_KEY_REQUEST: dict(start.request),
            GEN_KEY_WARNINGS: list(start.warnings),
            GEN_KEY_IMAGE_SLOTS: start.image_slots,
            GEN_KEY_IMAGE_COUNT: 0,
            GEN_KEY_MODE: start.mode,
            # Carried across attempts: the cost cap is per post, not per run.
            GEN_KEY_IMAGE_SPEND_USD: image_spend_of(metadata),
        },
    )


def heartbeat(metadata: object, now: str) -> dict[str, object]:
    """Stamp ``heartbeat_at``."""
    return _with_generation(
        metadata, {**generation_of(metadata), GEN_KEY_HEARTBEAT_AT: now}
    )


def with_voice_score(metadata: object, voice_score: float | None) -> dict[str, object]:
    """Mirror ``content.quality.voice_score`` for the listing/editor badge."""
    base = dict(metadata) if isinstance(metadata, dict) else {}
    if voice_score is None:
        return base
    return {**base, METADATA_KEY_VOICE_SCORE: voice_score}


def finished(
    metadata: object, outcome: GenerationOutcome, now: str
) -> dict[str, object]:
    """The final status of the attempt; the lease stays (it is still this run's)."""
    errors = [{**error, ERROR_KEY_AT: now} for error in outcome.errors]
    return _with_generation(
        metadata,
        {
            **generation_of(metadata),
            GEN_KEY_STATUS: outcome.status,
            GEN_KEY_FINISHED_AT: now,
            GEN_KEY_HEARTBEAT_AT: now,
            GEN_KEY_ERRORS: errors,
            GEN_KEY_RECOVERABLE: outcome.recoverable,
            GEN_KEY_IMAGE_COUNT: outcome.image_count,
            GEN_KEY_IMAGE_SPEND_USD: image_spend_of(metadata) + outcome.image_spend_usd,
        },
    )


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def is_stale(metadata: object, cutoff: datetime) -> bool:
    """An in-progress run whose heartbeat is older than ``cutoff`` (or missing)."""
    if status_of(metadata) != GENERATION_STATUS_IN_PROGRESS:
        return False
    beat = _parse_time(generation_of(metadata).get(GEN_KEY_HEARTBEAT_AT))
    return beat is None or beat < cutoff


def reaped(metadata: object, now: str) -> dict[str, object]:
    """A run killed by a restart: failed, recoverable, lease revoked."""
    error = {
        ERROR_KEY_CODE: ERR_GENERATION_INTERRUPTED,
        ERROR_KEY_REASON: ERR_GENERATION_INTERRUPTED,
        ERROR_KEY_AT: now,
    }
    return _with_generation(
        metadata,
        {
            **generation_of(metadata),
            GEN_KEY_STATUS: GENERATION_STATUS_FAILED,
            GEN_KEY_FINISHED_AT: now,
            GEN_KEY_LEASE_ID: None,
            GEN_KEY_ERRORS: [error],
            GEN_KEY_RECOVERABLE: True,
        },
    )


__all__ = [
    "GenerationStart",
    "finished",
    "generation_of",
    "heartbeat",
    "image_spend_of",
    "is_stale",
    "lease_of",
    "reaped",
    "started",
    "status_of",
    "with_voice_score",
]
