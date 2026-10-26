"""Fresh target reads and compatible-manual-run lookup for recovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_PENDING
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.autopilot.domain.dead_letter import is_dead_letter
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.generation_queue.constants import (
    ACTIVE_STATUSES,
    PAYLOAD_MANUAL_REPLACES_RUN_ID,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    ManualReprocessCommand,
    ProjectRecoveryState,
    RecoverySnapshot,
    is_manual_run,
)
from rag_backend.modules.generation_queue.domain.models import (
    GenerationKind,
    GenerationRun,
    is_active,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)
from rag_backend.modules.generation_queue.infrastructure.repository import run_from_row


@dataclass(frozen=True)
class AutopilotRecoveryFacts:
    """Current identity, project attribution, state and parked status."""

    run_id: str | None = None
    project_id: str | None = None
    dead: bool | None = None
    state: str | None = None


class ManualRecoveryReader:
    """Read all recovery state on the caller's session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(self, command: ManualReprocessCommand) -> RecoverySnapshot:
        """Load a target, its current project and its latest/active fences."""
        run = await self._target(command)
        autopilot = await self._autopilot(command, run)
        project_id, mismatch = _project_id(command, run, autopilot)
        project = await self._project(project_id)
        latest_id, active_id = await self._run_scope(project_id, run)
        missing = mismatch or (command.run_id is not None and run is None)
        missing = missing or (command.project_id is not None and project is None)
        return RecoverySnapshot(
            command=command,
            run=run,
            project=project,
            latest_run_id=latest_id,
            active_run_id=active_id,
            autopilot_dead=autopilot.dead,
            autopilot_run_id=autopilot.run_id,
            autopilot_state=autopilot.state,
            missing=missing,
        )

    async def serialize(self, snapshot: RecoverySnapshot) -> RecoverySnapshot:
        """Lock the original run or orphan project, then re-read all state."""
        command = snapshot.command
        if snapshot.run is not None:
            await self._session.get(
                GenerationRunModel,
                snapshot.run.id,
                with_for_update=True,
                populate_existing=True,
            )
        elif snapshot.project is not None:
            await self._session.get(
                CarouselProjectModel,
                snapshot.project.id,
                with_for_update=True,
                populate_existing=True,
            )
        return await self.load(command)

    async def run_by_id(self, run_id: UUID) -> GenerationRun | None:
        """Read one generation row freshly by its durable id."""
        row = await self._session.get(
            GenerationRunModel, run_id, populate_existing=True
        )
        return run_from_row(row) if row is not None else None

    async def active_by_dedupe(self, dedupe_key: str) -> GenerationRun | None:
        """Read an active staged run by its dedupe identity."""
        row = await self._session.scalar(
            select(GenerationRunModel)
            .where(
                GenerationRunModel.dedupe_key == dedupe_key,
                GenerationRunModel.status.in_(ACTIVE_STATUSES),
            )
            .execution_options(populate_existing=True)
        )
        return run_from_row(row) if row is not None else None

    async def find_existing(self, snapshot: RecoverySnapshot) -> GenerationRun | None:
        """Find a compatible active manual original or failed-terminal successor."""
        rows = await self._session.scalars(
            select(GenerationRunModel)
            .where(GenerationRunModel.status.in_(ACTIVE_STATUSES))
            .order_by(GenerationRunModel.created_at.desc())
            .execution_options(populate_existing=True)
        )
        for row in rows:
            run = run_from_row(row)
            if is_manual_run(run) and _compatible(snapshot, run):
                return run
        return None

    async def _target(self, command: ManualReprocessCommand) -> GenerationRun | None:
        if command.run_id is not None:
            return await self.run_by_id(command.run_id)
        if command.project_id is None:
            return None
        row = await self._session.scalar(
            select(GenerationRunModel)
            .where(GenerationRunModel.carousel_project_id == command.project_id)
            .order_by(
                GenerationRunModel.created_at.desc(), GenerationRunModel.id.desc()
            )
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return run_from_row(row) if row is not None else None

    async def _autopilot(
        self, command: ManualReprocessCommand, run: GenerationRun | None
    ) -> AutopilotRecoveryFacts:
        if run is not None and run.kind is not GenerationKind.AUTOPILOT_DRIVE:
            return AutopilotRecoveryFacts()
        if run is not None and run.autopilot_run_id is None:
            return AutopilotRecoveryFacts(dead=False)
        if run is not None:
            return await self._autopilot_by_id(run.autopilot_run_id or "")
        if command.project_id is None:
            return AutopilotRecoveryFacts()
        row = await self._session.scalar(
            select(AutopilotRunModel)
            .where(AutopilotRunModel.carousel_project_id == command.project_id)
            .order_by(AutopilotRunModel.created_at.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return _autopilot_facts(row)

    async def _autopilot_by_id(self, run_id: str) -> AutopilotRecoveryFacts:
        try:
            autopilot_id = UUID(run_id)
        except ValueError:
            return AutopilotRecoveryFacts(dead=False)
        row = await self._session.get(
            AutopilotRunModel, autopilot_id, populate_existing=True
        )
        if row is None:
            return AutopilotRecoveryFacts(dead=False)
        return _autopilot_facts(row)

    async def _project(self, project_id: str | None) -> ProjectRecoveryState | None:
        if project_id is None:
            return None
        row = await self._session.get(
            CarouselProjectModel, project_id, populate_existing=True
        )
        if row is None:
            return None
        return ProjectRecoveryState(
            id=str(row.id),
            title=str(row.title or row.topic),
            phase_status=str(row.phase_status or PHASE_STATUS_PENDING),
            lock_version=int(row.lock_version or 1),
            heartbeat_at=row.run_heartbeat_at,
            updated_at=cast(datetime, row.updated_at),
        )

    async def _run_scope(
        self, project_id: str | None, run: GenerationRun | None
    ) -> tuple[UUID | None, UUID | None]:
        scope = _scope(project_id, run)
        if scope is None:
            active = run.id if run is not None and is_active(run.status) else None
            return (run.id if run is not None else None), active
        latest = await self._session.scalar(
            select(GenerationRunModel.id)
            .where(scope)
            .order_by(
                GenerationRunModel.created_at.desc(), GenerationRunModel.id.desc()
            )
            .limit(1)
        )
        active = await self._session.scalar(
            select(GenerationRunModel.id)
            .where(scope, GenerationRunModel.status.in_(ACTIVE_STATUSES))
            .order_by(
                GenerationRunModel.created_at.desc(), GenerationRunModel.id.desc()
            )
            .limit(1)
        )
        return _uuid_or_none(latest), _uuid_or_none(active)


def _autopilot_facts(row: AutopilotRunModel | None) -> AutopilotRecoveryFacts:
    if row is None:
        return AutopilotRecoveryFacts()
    return AutopilotRecoveryFacts(
        run_id=str(row.id),
        project_id=row.carousel_project_id,
        dead=is_dead_letter(row.state_reason),
        state=str(row.state),
    )


def _scope(
    project_id: str | None, run: GenerationRun | None
) -> ColumnElement[bool] | None:
    if project_id is not None:
        return GenerationRunModel.carousel_project_id == project_id
    if run is not None and run.autopilot_run_id is not None:
        return GenerationRunModel.autopilot_run_id == run.autopilot_run_id
    return None


def _project_id(
    command: ManualReprocessCommand,
    run: GenerationRun | None,
    autopilot: AutopilotRecoveryFacts,
) -> tuple[str | None, bool]:
    attributed = autopilot.project_id
    if attributed is None and run is not None:
        attributed = run.carousel_project_id
    project_id = attributed or command.project_id
    mismatch = bool(
        command.project_id and run is not None and command.project_id != attributed
    )
    return project_id, mismatch


def _compatible(snapshot: RecoverySnapshot, run: GenerationRun) -> bool:
    command = snapshot.command
    if command.run_id is not None:
        replaced = run.payload.get(PAYLOAD_MANUAL_REPLACES_RUN_ID)
        if run.id == command.run_id or replaced == str(command.run_id):
            return True
    project_id = snapshot.project.id if snapshot.project is not None else None
    if project_id is not None and run.carousel_project_id == project_id:
        return True
    original = snapshot.run
    return bool(
        original is not None
        and original.autopilot_run_id
        and run.autopilot_run_id == original.autopilot_run_id
    )


def _uuid_or_none(value: object) -> UUID | None:
    if value is None:
        return None
    return value if isinstance(value, UUID) else UUID(str(value))


__all__ = ["ManualRecoveryReader"]
