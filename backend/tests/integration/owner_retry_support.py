"""Seeds, a fake workflow engine and readers for the owner Retry tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models import UserModel
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.editorial.public import (
    CarouselProjectWriteOwner,
    EditorialWorkflowEngine,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from tests.integration.manual_reprocess_support import NOW
from tests.integration.pg_schema_support import isolated_schema
from tests.integration.queue_flow_db_support import QUEUE_FLOW_TABLES, on_postgres

RETRY_EVENT = "carousel.retry.requested"
OWNER_ID = "owner-user"


@dataclass
class FakeEngine:
    """The engine calls a Retry makes: checkpoint read, parked check, flip."""

    state: dict[str, object] | None
    parked: bool = False
    flipped: list[str] = field(default_factory=list)

    async def get_workflow_state(self, project_id: str) -> dict[str, object] | None:
        """The checkpoint state, or None when there is none."""
        del project_id
        return self.state

    async def is_parked_before_node(self, project_id: str) -> bool:
        """Whether a node waits to be re-driven."""
        del project_id
        return self.parked

    async def mark_resume_in_progress(self, project_id: str, db: AsyncSession) -> str:
        """Flip the row to in_progress through the write owner, like the engine."""
        state = self.state or {}
        phase = str(state.get("current_phase", ""))
        await CarouselProjectWriteOwner(db).sync_phase(
            project_id, {"current_phase": phase, "phase_status": "in_progress"}
        )
        self.flipped.append(project_id)
        return phase

    def typed(self) -> EditorialWorkflowEngine:
        """The fake as the engine type the Retry expects."""
        return cast(EditorialWorkflowEngine, self)


@asynccontextmanager
async def retry_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """The queue-flow tables plus notifications (the revision-cap escalation)."""
    if on_postgres():
        async with isolated_schema((*QUEUE_FLOW_TABLES, "notifications")) as engine:
            yield engine
        return
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'retry.db'}", poolclass=NullPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


async def seed_owner(session: AsyncSession) -> None:
    """The carousel owner's user row."""
    if await session.get(UserModel, OWNER_ID) is not None:
        return
    session.add(
        UserModel(
            id=OWNER_ID,
            email="owner@ae0606.test",
            full_name="Owner",
            hashed_password="hash",
            role=UserRole.EDITOR.value,
        )
    )
    await session.flush()


async def seed_autopilot(
    session: AsyncSession, project_id: str, state: str, reason: str
) -> UUID:
    """A topic and an autopilot run on ``project_id`` in ``state``."""
    topic_id, run_id = uuid4(), uuid4()
    session.add(
        TopicCandidateModel(
            id=topic_id,
            title="Safe title",
            angle="Angle",
            why_viral="Why",
            audience="Builders",
            niche="AI",
            brief="Brief",
            sources=[],
            score=90,
            signal_hash=uuid4().hex,
            status="promoted",
            created_at=NOW - timedelta(hours=2),
        )
    )
    await session.flush()
    session.add(
        AutopilotRunModel(
            id=run_id,
            topic_candidate_id=topic_id,
            carousel_project_id=project_id,
            state=state,
            state_reason=reason,
            publish_attempts=0,
            start_attempts=0,
            telegram_message_ids=[],
            created_at=NOW - timedelta(hours=1),
            updated_at=NOW - timedelta(hours=1),
        )
    )
    await session.flush()
    return run_id


async def retry_audits(session: AsyncSession) -> list[WorkflowAuditLogModel]:
    """Every ``carousel.retry.requested`` audit row."""
    rows = await session.scalars(
        select(WorkflowAuditLogModel).where(
            WorkflowAuditLogModel.event_type == RETRY_EVENT
        )
    )
    return list(rows.all())


async def staged_runs(
    session: AsyncSession, project_id: str
) -> list[GenerationRunModel]:
    """The generation runs staged for ``project_id``."""
    rows = await session.scalars(
        select(GenerationRunModel).where(
            GenerationRunModel.carousel_project_id == project_id
        )
    )
    return list(rows.all())


async def autopilot_state(session: AsyncSession, run_id: UUID) -> tuple[str, str]:
    """The run's state and reason, read fresh."""
    row = await session.get(AutopilotRunModel, run_id, populate_existing=True)
    assert row is not None
    return str(row.state), str(row.state_reason or "")
