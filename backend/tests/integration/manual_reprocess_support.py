"""Seed and assertion helpers for manual carousel recovery integration tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    MaintenanceNotice,
)
from rag_backend.modules.generation_queue.domain.models import (
    ATTEMPT_ID_KEY,
    GenerationKind,
    GenerationStatus,
    WorkflowResumePayload,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)

NOW = datetime.now(UTC)
OLD = NOW - timedelta(seconds=601)
REPROCESS_EVENT = "carousel.reprocess.requested"


@dataclass
class RecordingNotifier:
    """Record maintenance requests and report a configurable result."""

    notified: bool = True
    error: Exception | None = None
    notices: list[MaintenanceNotice] = field(default_factory=list)

    async def notify(self, notice: MaintenanceNotice) -> bool:
        """Record one post-commit notification."""
        self.notices.append(notice)
        if self.error is not None:
            raise self.error
        return self.notified


def project_row(
    project_id: str, owner_id: str | None = None, **overrides: object
) -> CarouselProjectModel:
    """A generating carousel project with field overrides."""
    values: dict[str, object] = {
        "id": project_id,
        "owner_id": owner_id,
        "topic": "Safe topic",
        "title": "Safe title",
        "audience": "Builders",
        "niche": "AI",
        "current_phase": "content",
        "phase_status": PHASE_STATUS_IN_PROGRESS,
        "lock_version": 4,
        "run_heartbeat_at": NOW,
        "created_at": NOW - timedelta(days=1),
        "updated_at": OLD,
    }
    values.update(overrides)
    return CarouselProjectModel(**values)


def workflow_run_row(
    project_id: str, status: GenerationStatus, **overrides: object
) -> GenerationRunModel:
    """A workflow-resume generation row with safe payload data."""
    run_id = overrides.pop("id", uuid4())
    attempt_id = overrides.pop(ATTEMPT_ID_KEY, None)
    payload = WorkflowResumePayload(
        project_id=project_id,
        action="approve",
        reviewer_id="reviewer",
        project_title="Safe title",
    ).dump()
    if attempt_id is not None:
        payload[ATTEMPT_ID_KEY] = str(attempt_id)
    values: dict[str, object] = {
        "id": run_id,
        "kind": GenerationKind.WORKFLOW_RESUME.value,
        "dedupe_key": f"resume:{project_id}:4",
        "status": status.value,
        "payload": payload,
        "carousel_project_id": project_id,
        "attempts": 2,
        "phase_attempts": {"content": 1, "start": 1},
        "last_phase": "content",
        "created_at": NOW - timedelta(minutes=5),
        "updated_at": NOW - timedelta(minutes=5),
    }
    values.update(overrides)
    return GenerationRunModel(**values)


def autopilot_run_row(
    autopilot_id: UUID, status: GenerationStatus, **overrides: object
) -> GenerationRunModel:
    """An autopilot-drive generation row."""
    values: dict[str, object] = {
        "id": uuid4(),
        "kind": GenerationKind.AUTOPILOT_DRIVE.value,
        "dedupe_key": f"autopilot:{autopilot_id}",
        "status": status.value,
        "payload": {"autopilot_run_id": str(autopilot_id)},
        "autopilot_run_id": str(autopilot_id),
        "attempts": 1,
        "phase_attempts": {"start": 1},
        "last_phase": "start",
        "created_at": NOW - timedelta(minutes=5),
        "updated_at": NOW - timedelta(minutes=5),
    }
    values.update(overrides)
    return GenerationRunModel(**values)


async def reprocess_audits(session: AsyncSession) -> list[WorkflowAuditLogModel]:
    """All manual reprocess audit rows."""
    rows = await session.scalars(
        select(WorkflowAuditLogModel).where(
            WorkflowAuditLogModel.event_type == REPROCESS_EVENT
        )
    )
    return list(rows.all())
