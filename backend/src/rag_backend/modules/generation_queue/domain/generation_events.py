"""Bounded generation-event values and sanitization."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Protocol, TypeAlias
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from rag_backend.modules.generation_queue.domain.models import GenerationKind

EVENT_WRITE_TIMEOUT_SECONDS = 0.1
EVENT_DETAILS_MAX_BYTES = 4096
EVENT_DETAIL_MAX_FIELDS = 24
EVENT_DETAIL_INPUT_MAX_FIELDS = 64
EVENT_DETAIL_KEY_MAX_CHARS = 64
EVENT_TRACE_URL_MAX_CHARS = 512
_SAFE_CODE = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_SAFE_UUID = re.compile(r"[0-9a-fA-F-]{36}")
_SAFE_SIZE = re.compile(r"[0-9]{1,5}x[0-9]{1,5}")
_MODEL_SAFE_VALUES = frozenset({"gpt-image-2", "gemini-3.1-flash-image-preview"})
_EVENT_STRING_MAX_CHARS = 120
_EVENT_ATTEMPT_MAX = 32767
_PROVIDER_SAFE_VALUES = frozenset({"grokbot", "openai", "openai_fallback", "gemini"})
_LANGUAGE_SAFE_VALUES = frozenset({"pt", "en"})
_UNKNOWN = "unknown"
_MAX_INT64 = 2**63 - 1

EventDetail: TypeAlias = str | int | float | bool

_ALLOWED_DETAIL_KEYS = frozenset({
    "action",
    "attempt",
    "autopilot_run_id",
    "blocking_count",
    "byte_count",
    "delay_seconds",
    "error_type",
    "failed_count",
    "image_job_id",
    "job_status",
    "language",
    "lowest_score",
    "model",
    "page_count",
    "policy_version",
    "provider",
    "reason",
    "result",
    "resumed",
    "reused",
    "score",
    "scored_count",
    "size",
    "slide_index",
    "status",
    "total_count",
    "truncated",
    "unscored_count",
    "violation_count",
})


@dataclass(frozen=True, kw_only=True)
class GenerationEventRun:
    """The run identity needed by one event write."""

    id: UUID
    kind: GenerationKind
    carousel_project_id: str | None
    autopilot_run_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class GenerationEventInput:
    """One diagnostic observation before persistence."""

    event_type: str
    outcome: str
    id: UUID = field(default_factory=uuid4)
    phase: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    duration_ms: int | None = None
    attempt: int | None = None
    error_code: str | None = None
    message_code: str | None = None
    details: dict[str, object] = field(default_factory=dict)
    langfuse_trace_id: str | None = None
    langfuse_trace_url: str | None = None


@dataclass(frozen=True, kw_only=True)
class GenerationEvent(GenerationEventInput):
    """A stored event and its carousel/run correlation."""

    generation_run_id: UUID
    carousel_project_id: str
    kind: GenerationKind


@dataclass(frozen=True, kw_only=True)
class GenerationRunSummary:
    """The safe current-run fields shown alongside a page of events."""

    id: UUID
    kind: GenerationKind
    status: str
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    attempts: int
    error_code: str | None


@dataclass(frozen=True, kw_only=True)
class GenerationLogQuery:
    """One bounded keyset page requested for an authorized carousel."""

    project_id: str
    limit: int = 50
    before: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class GenerationLogPage:
    """Events and only the run summaries referenced by that page."""

    events: tuple[GenerationEvent, ...]
    runs: tuple[GenerationRunSummary, ...]
    next_cursor: UUID | None


class InvalidGenerationEventCursorError(ValueError):
    """A cursor that does not belong to the authorized carousel."""


class GenerationRunCompletion(Protocol):
    """A best-effort existing-stream refresh after terminal persistence."""

    async def completed(self, project_id: str, *, succeeded: bool = True) -> None:
        """Notify listeners that one run has settled with its outcome."""
        ...


class GenerationEventRecorder(Protocol):
    """A best-effort event destination."""

    async def record(
        self, run: GenerationEventRun, event: GenerationEventInput
    ) -> bool:
        """Persist one event, returning whether it was stored."""
        ...


def sanitize_event_details(details: dict[str, object]) -> dict[str, EventDetail]:
    """Keep only bounded scalar diagnostics and mark every omission."""
    sanitized: dict[str, EventDetail] = {}
    truncated = False
    for index, (key, value) in enumerate(details.items()):
        if index >= EVENT_DETAIL_INPUT_MAX_FIELDS:
            truncated = True
            break
        if len(sanitized) >= EVENT_DETAIL_MAX_FIELDS:
            truncated = True
            break
        if not _valid_detail_key(key):
            truncated = True
            continue
        safe = _detail_value(key, value)
        if safe is None:
            truncated = True
            continue
        sanitized[key] = safe
    if truncated:
        if len(sanitized) >= EVENT_DETAIL_MAX_FIELDS:
            sanitized.pop(next(reversed(sanitized)))
        sanitized["truncated"] = True
    if _details_size(sanitized) > EVENT_DETAILS_MAX_BYTES:
        return {"truncated": True}
    return sanitized


def sanitize_event(event: GenerationEventInput) -> GenerationEventInput:
    """Bound every free field before the event reaches the database."""
    return replace(
        event,
        event_type=_code(event.event_type),
        outcome=_code(event.outcome, 24),
        phase=_optional_code(event.phase),
        duration_ms=_optional_nonnegative(event.duration_ms),
        attempt=_optional_attempt(event.attempt),
        error_code=_optional_code(event.error_code),
        message_code=_optional_code(event.message_code),
        details=dict[str, object](sanitize_event_details(event.details)),
        langfuse_trace_id=_optional_text(event.langfuse_trace_id, 128),
        langfuse_trace_url=_trace_url(event.langfuse_trace_url),
    )


def _valid_detail_key(key: object) -> bool:
    return (
        isinstance(key, str)
        and len(key) <= EVENT_DETAIL_KEY_MAX_CHARS
        and key in _ALLOWED_DETAIL_KEYS
    )


def _detail_value(key: str, value: object) -> EventDetail | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value if abs(value) <= _MAX_INT64 else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if not isinstance(value, str):
        return None
    return _detail_string(key, value)


def _detail_string(key: str, value: str) -> str | None:
    if len(value) > _EVENT_STRING_MAX_CHARS:
        return None
    normalized = " ".join(value.split())
    if key in {
        "autopilot_run_id",
        "image_job_id",
        "size",
        "model",
        "provider",
        "language",
    }:
        return _special_detail_string(key, normalized)
    return normalized if _SAFE_CODE.fullmatch(normalized) else None


def _special_detail_string(key: str, value: str) -> str | None:
    if key in {"autopilot_run_id", "image_job_id"}:
        return value if _SAFE_UUID.fullmatch(value) else None
    if key == "size":
        return value if _SAFE_SIZE.fullmatch(value) else None
    if key == "model":
        return value if value in _MODEL_SAFE_VALUES else None
    if key == "provider":
        return value if value in _PROVIDER_SAFE_VALUES else None
    return value if value in _LANGUAGE_SAFE_VALUES else None


def _code(value: str, cap: int = 64) -> str:
    if len(value) > cap:
        return _UNKNOWN
    return value if _SAFE_CODE.fullmatch(value) else _UNKNOWN


def _optional_code(value: str | None) -> str | None:
    if value is None:
        return None
    return _code(value)


def _optional_nonnegative(value: int | None) -> int | None:
    if value is None or value < 0 or value > _MAX_INT64:
        return None
    return value


def _optional_attempt(value: int | None) -> int | None:
    if value is None or value < 0 or value > _EVENT_ATTEMPT_MAX:
        return None
    return value


def _optional_text(value: str | None, cap: int) -> str | None:
    if value is None or len(value) > cap:
        return None
    normalized = " ".join(value.split())
    return normalized or None


def _trace_url(value: str | None) -> str | None:
    if value is None or len(value) > EVENT_TRACE_URL_MAX_CHARS:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    return value


def _details_size(details: dict[str, EventDetail]) -> int:
    return len(
        json.dumps(details, separators=(",", ":"), allow_nan=False).encode("utf-8")
    )


__all__ = [
    "EVENT_DETAILS_MAX_BYTES",
    "EVENT_WRITE_TIMEOUT_SECONDS",
    "EventDetail",
    "GenerationEvent",
    "GenerationEventInput",
    "GenerationEventRecorder",
    "GenerationEventRun",
    "GenerationLogPage",
    "GenerationLogQuery",
    "GenerationRunCompletion",
    "GenerationRunSummary",
    "InvalidGenerationEventCursorError",
    "sanitize_event",
    "sanitize_event_details",
]
