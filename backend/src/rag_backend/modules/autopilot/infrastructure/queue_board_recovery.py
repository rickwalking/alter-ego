"""Safe manual-recovery capabilities for staged and synthetic panel rows."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot.domain.queue_board import GenerationRow
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    ManualReprocessCommand,
    RecoveryCapability,
    RefusalCode,
)

if TYPE_CHECKING:
    from rag_backend.modules.generation_queue.application.manual_reprocess import (
        ManualRecoveryService,
    )

_PANEL_ACTOR = "queue-panel"


async def enrich_recovery(
    session: AsyncSession, rows: list[GenerationRow]
) -> list[GenerationRow]:
    """Use the existing inspector so panel and workspace refusal semantics agree."""
    from rag_backend.modules.generation_queue.public import build_manual_recovery

    service = build_manual_recovery(session)
    return [await _recover_row(service, row) for row in rows]


async def _recover_row(
    service: ManualRecoveryService, row: GenerationRow
) -> GenerationRow:
    if not row.staged and row.carousel_project_id is None:
        return replace(
            row,
            can_reprocess=False,
            refusal_code=RefusalCode.PROJECTLESS_UNSTAGED.value,
            stuck_kind=None,
            lock_version=None,
        )
    capability = await service.inspect(_command(row))
    return _with_capability(row, capability)


def _command(row: GenerationRow) -> ManualReprocessCommand:
    if row.staged:
        return ManualReprocessCommand(
            project_id=None, run_id=UUID(row.id), actor_id=_PANEL_ACTOR
        )
    return ManualReprocessCommand(
        project_id=row.carousel_project_id, run_id=None, actor_id=_PANEL_ACTOR
    )


def _with_capability(
    row: GenerationRow, capability: RecoveryCapability
) -> GenerationRow:
    refusal = capability.refusal.value if capability.refusal is not None else None
    stuck = capability.stuck_kind.value if capability.stuck_kind is not None else None
    return replace(
        row,
        can_reprocess=capability.can_reprocess,
        refusal_code=refusal,
        stuck_kind=stuck,
        lock_version=capability.lock_version,
    )


__all__ = ["enrich_recovery"]
