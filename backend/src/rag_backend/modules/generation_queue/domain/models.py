"""Generation run: the queue's own record of one unit of carousel work.

``generation_runs`` is the source of truth for Telegram, the dashboard and
idempotency (ADR-0026); PgQueuer only transports the work. ``attempts`` counts
the starts that made no progress over the run's life, ``phase_attempts`` the
consecutive unfinished starts of each phase: a phase that finishes cleanly drops
its counter, so a run that keeps advancing is never taken for poison.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from rag_backend.modules.generation_queue.constants import (
    ACTIVE_STATUSES,
    DEDUPE_AUTOPILOT,
    DEDUPE_RESUME,
    ERR_PAYLOAD_FIELD,
    KIND_AUTOPILOT_DRIVE,
    KIND_WORKFLOW_RESUME,
    STATUS_CANCELLED,
    STATUS_DEAD_LETTER,
    STATUS_QUEUED,
    STATUS_RETRY_WAIT,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
)
from rag_backend.modules.generation_queue.domain.budget import AttemptCounts


class GenerationKind(StrEnum):
    """What a generation run drives."""

    AUTOPILOT_DRIVE = KIND_AUTOPILOT_DRIVE
    WORKFLOW_RESUME = KIND_WORKFLOW_RESUME


class GenerationStatus(StrEnum):
    """Lifecycle of a generation run."""

    QUEUED = STATUS_QUEUED
    RUNNING = STATUS_RUNNING
    RETRY_WAIT = STATUS_RETRY_WAIT
    SUCCEEDED = STATUS_SUCCEEDED
    DEAD_LETTER = STATUS_DEAD_LETTER
    CANCELLED = STATUS_CANCELLED


def is_active(status: GenerationStatus) -> bool:
    """Queued, running or waiting for a retry: the dedupe key is taken."""
    return status.value in ACTIVE_STATUSES


@dataclass(frozen=True)
class AutopilotDrivePayload:
    """Step one autopilot run until it waits for the owner or ends."""

    autopilot_run_id: str

    @classmethod
    def parse(cls, data: Mapping[str, object]) -> AutopilotDrivePayload:
        """Validate a stored payload; ``ValueError`` when it is malformed."""
        return cls(autopilot_run_id=_required_str(data, "autopilot_run_id"))

    def dump(self) -> dict[str, object]:
        """The JSON payload stored on the run."""
        return {"autopilot_run_id": self.autopilot_run_id}


@dataclass(frozen=True, kw_only=True)
class WorkflowResumePayload:
    """A dashboard approve, revise or re-drive accepted by the web route."""

    project_id: str
    action: str
    reviewer_id: str
    feedback: str | None = None
    project_title: str = ""
    structured_feedback: dict[str, object] | None = None

    @classmethod
    def parse(cls, data: Mapping[str, object]) -> WorkflowResumePayload:
        """Validate a stored payload; ``ValueError`` when it is malformed."""
        feedback = data.get("feedback")
        structured = data.get("structured_feedback")
        if feedback is not None and not isinstance(feedback, str):
            raise ValueError(ERR_PAYLOAD_FIELD.format(field="feedback"))
        if structured is not None and not isinstance(structured, dict):
            raise ValueError(ERR_PAYLOAD_FIELD.format(field="structured_feedback"))
        return cls(
            project_id=_required_str(data, "project_id"),
            action=_required_str(data, "action"),
            reviewer_id=_required_str(data, "reviewer_id"),
            feedback=feedback,
            project_title=str(data.get("project_title") or ""),
            structured_feedback=structured,
        )

    def dump(self) -> dict[str, object]:
        """The JSON payload stored on the run."""
        return {
            "project_id": self.project_id,
            "action": self.action,
            "reviewer_id": self.reviewer_id,
            "feedback": self.feedback,
            "project_title": self.project_title,
            "structured_feedback": self.structured_feedback,
        }


def _required_str(data: Mapping[str, object], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(ERR_PAYLOAD_FIELD.format(field=name))
    return value


@dataclass(frozen=True, kw_only=True)
class StageCommand:
    """One unit of work to record, in the caller's transaction."""

    kind: GenerationKind
    dedupe_key: str
    payload: dict[str, object]
    autopilot_run_id: str | None = None
    carousel_project_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class GenerationRun:
    """A stored generation run."""

    id: UUID
    kind: GenerationKind
    dedupe_key: str
    status: GenerationStatus
    payload: dict[str, object]
    autopilot_run_id: str | None = None
    carousel_project_id: str | None = None
    pgq_job_id: int | None = None
    attempts: int = 0
    phase_attempts: dict[str, int] = field(default_factory=dict)
    last_phase: str | None = None
    last_error_code: str | None = None
    created_at: datetime | None = None

    @property
    def counts(self) -> AttemptCounts:
        """The attempt counters as a budget value."""
        return AttemptCounts(
            attempts=self.attempts, phase_attempts=dict(self.phase_attempts)
        )


@dataclass(frozen=True, kw_only=True)
class CountsUpdate:
    """New attempt counters and the phase they were counted for."""

    counts: AttemptCounts
    phase: str


@dataclass(frozen=True, kw_only=True)
class DeadLetterCommand:
    """Park a run with its classified reason."""

    run_id: UUID
    error_code: str
    error: str


@dataclass(frozen=True, kw_only=True)
class RetryCommand:
    """Put a run back to wait for its next attempt."""

    run_id: UUID
    next_attempt_at: datetime
    error_code: str
    error: str


@dataclass(frozen=True, kw_only=True)
class HeldJob:
    """A PgQueuer job held as ``failed`` (our dead letter on its side)."""

    job_id: int
    generation_run_id: UUID | None
    error: str = ""


def autopilot_stage(run_id: str, project_id: str | None = None) -> StageCommand:
    """The stage command for driving one autopilot run."""
    return StageCommand(
        kind=GenerationKind.AUTOPILOT_DRIVE,
        dedupe_key=DEDUPE_AUTOPILOT.format(run_id=run_id),
        payload=AutopilotDrivePayload(autopilot_run_id=run_id).dump(),
        autopilot_run_id=run_id,
        carousel_project_id=project_id,
    )


def resume_stage(payload: WorkflowResumePayload, lock_version: int) -> StageCommand:
    """The stage command for one dashboard resume at a known lock version."""
    return StageCommand(
        kind=GenerationKind.WORKFLOW_RESUME,
        dedupe_key=DEDUPE_RESUME.format(
            project_id=payload.project_id, lock_version=lock_version
        ),
        payload=payload.dump(),
        carousel_project_id=payload.project_id,
    )
