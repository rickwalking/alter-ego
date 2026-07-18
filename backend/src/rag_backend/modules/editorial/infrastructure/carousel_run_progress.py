"""Run-progress persistence helpers for the background resume task (AE-0315).

The background resume runner (application layer) captures its run-ownership
token here at task start and heartbeats ``run_heartbeat_at`` while alive. The
heartbeat is a raw Core UPDATE that is **self-fencing**: its WHERE clause pins
the captured ``run_epoch`` and ``phase_status = in_progress``, so a zombie's
beat after a reap matches zero rows (enumerated raw-SQL site in the AE-0315
write-site survey; allowlisted by the raw-UPDATE lint gate).

Lives in the editorial module's infrastructure layer (alongside the AE-0107
write owner) so the application layer keeps importing run persistence through
``modules.editorial.public`` — no new application→infrastructure edge for the
architecture ratchet.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast

import structlog
from sqlalchemy import CursorResult, select, update

from rag_backend.domain.constants.carousel_run import (
    LOG_EVENT_RUN_HEARTBEAT_FAILED,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.domain.models.carousel_run import CarouselRunContext
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.pg_lock_timeout import (
    apply_run_write_lock_timeout,
)

logger = structlog.get_logger()

# In-task heartbeat retry policy: a single transient DB blip must not look
# like death (pinned cold-critic r5); the reaper additionally requires N
# consecutive stale observations.
_HEARTBEAT_WRITE_ATTEMPTS = 3
_HEARTBEAT_RETRY_DELAY_SECONDS = 1.0


async def read_run_fence(project_id: str) -> CarouselRunContext | None:
    """Capture the run-ownership token (current epoch) at run start."""
    session_factory = get_session_maker()
    async with session_factory() as session:
        result = await session.execute(
            select(CarouselProjectModel.run_epoch).where(
                CarouselProjectModel.id == project_id
            )
        )
        epoch = result.scalar_one_or_none()
    if epoch is None:
        return None
    return CarouselRunContext(project_id=project_id, epoch=int(epoch))


async def write_run_heartbeat(project_id: str, epoch: int) -> bool:
    """Stamp ``run_heartbeat_at`` now; False when the fence no longer matches.

    AE-0320: the write carries a transaction-scoped ``lock_timeout`` so a beat
    issued while the resume runner's own session holds the row lock fails fast
    instead of self-deadlocking the run (prod incident 2026-07-18).
    """
    session_factory = get_session_maker()
    async with session_factory() as session:
        await apply_run_write_lock_timeout(session)
        result = await session.execute(
            update(CarouselProjectModel)
            .where(
                CarouselProjectModel.id == project_id,
                CarouselProjectModel.run_epoch == epoch,
                CarouselProjectModel.phase_status == PHASE_STATUS_IN_PROGRESS,
            )
            .values(run_heartbeat_at=datetime.now(UTC))
        )
        await session.commit()
        return cast(CursorResult[object], result).rowcount == 1


async def write_run_heartbeat_with_retry(project_id: str, epoch: int) -> bool:
    """Heartbeat with in-task retry on transient failure (never raises)."""
    for attempt in range(1, _HEARTBEAT_WRITE_ATTEMPTS + 1):
        try:
            return await write_run_heartbeat(project_id, epoch)
        except Exception as exc:
            logger.warning(
                LOG_EVENT_RUN_HEARTBEAT_FAILED,
                project_id=project_id,
                attempt=attempt,
                error=str(exc),
            )
            if attempt < _HEARTBEAT_WRITE_ATTEMPTS:
                await asyncio.sleep(_HEARTBEAT_RETRY_DELAY_SECONDS)
    return False


async def write_run_heartbeat_once(project_id: str, epoch: int) -> bool:
    """Single-attempt heartbeat that never raises (stage-boundary beats).

    AE-0320: the resume runner awaits stage-boundary beats INLINE while its
    main session may hold flushed-but-uncommitted row writes — those beats
    must be strictly bounded (one attempt, lock-timeout-capped) and soft-fail;
    liveness is owned by the interval heartbeat loop, not by stage beats.
    """
    try:
        return await write_run_heartbeat(project_id, epoch)
    except Exception as exc:
        logger.warning(
            LOG_EVENT_RUN_HEARTBEAT_FAILED,
            project_id=project_id,
            attempt=1,
            error=str(exc),
        )
        return False


__all__ = [
    "read_run_fence",
    "write_run_heartbeat",
    "write_run_heartbeat_once",
    "write_run_heartbeat_with_retry",
]
