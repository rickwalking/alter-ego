"""Generation-status CAS shared by manual recovery write paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from sqlalchemy import CursorResult, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.generation_queue.constants import STATUS_QUEUED
from rag_backend.modules.generation_queue.domain.manual_recovery import RecoveryMutation
from rag_backend.modules.generation_queue.domain.models import GenerationRun
from rag_backend.modules.generation_queue.infrastructure.manual_recovery_reader import (
    ManualRecoveryReader,
)
from rag_backend.modules.generation_queue.infrastructure.models import (
    GenerationRunModel,
)


@dataclass(frozen=True, kw_only=True)
class RecoveryRunCAS:
    """One expected-status transition with manual payload metadata."""

    mutation: RecoveryMutation
    run: GenerationRun
    expected_status: str
    payload: dict[str, object]


async def recovery_run_cas(
    session: AsyncSession, command: RecoveryRunCAS
) -> GenerationRun | None:
    """Queue the expected row and return its fresh state, or None on a CAS loss."""
    now = command.mutation.requested_at
    result = await session.execute(
        update(GenerationRunModel)
        .where(
            GenerationRunModel.id == command.run.id,
            GenerationRunModel.status == command.expected_status,
        )
        .values(
            status=STATUS_QUEUED,
            payload=command.payload,
            created_at=now,
            updated_at=now,
            next_attempt_at=None,
            finished_at=None,
        )
    )
    if cast(CursorResult[object], result).rowcount != 1:
        return None
    return await ManualRecoveryReader(session).run_by_id(command.run.id)


__all__ = ["RecoveryRunCAS", "recovery_run_cas"]
