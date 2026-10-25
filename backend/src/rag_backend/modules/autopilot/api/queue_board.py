"""The dashboard's queue panel API (admin only).

``GET /generation-runs`` returns the board; ``POST /generation-runs/{id}/retry``,
``/discard`` and ``/cancel`` and ``POST /generation-runs/backlog/{id}/generate``
apply one button. ``done`` answers 200, ``already_resolved`` and ``not_allowed``
409 (the body names the outcome), an unknown id 404.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import require_admin
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_WORKFLOW_ENDPOINTS
from rag_backend.modules.autopilot.api.schemas import (
    BacklogItemResponse,
    QueueActionResponse,
    QueueBoardResponse,
    QueueItemResponse,
)
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.queue_board_service import (
    QueueBoardDependencies,
    QueueBoardService,
)
from rag_backend.modules.autopilot.application.run_revive import ReviveDependencies
from rag_backend.modules.autopilot.infrastructure.backlog_store import SqlBacklogStore
from rag_backend.modules.autopilot.infrastructure.dead_letter_runs import (
    SqlDeadLetterRuns,
)
from rag_backend.modules.autopilot.infrastructure.queue_board_reader import (
    SqlQueueBoardReader,
)
from rag_backend.modules.autopilot.infrastructure.queue_control import SqlQueueControl
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.queue_constants import (
    OUTCOME_DONE,
    OUTCOME_NOT_FOUND,
    PATH_BACKLOG_GENERATE,
    PATH_GENERATION_RUN_CANCEL,
    PATH_GENERATION_RUN_DISCARD,
    PATH_GENERATION_RUN_RETRY,
    PATH_GENERATION_RUNS,
    QUEUE_BOARD_TAG,
)

router = APIRouter(tags=[QUEUE_BOARD_TAG], dependencies=[Depends(require_admin)])


@dataclass(frozen=True)
class _Panel:
    """The panel service and the session its buttons commit."""

    service: QueueBoardService
    session: AsyncSession


def _panel(session: Annotated[AsyncSession, Depends(get_db)]) -> _Panel:
    service = QueueBoardService(
        QueueBoardDependencies(
            reader=SqlQueueBoardReader(session),
            backlog=SqlBacklogStore(session),
            revive=ReviveDependencies(
                runs=SqlAlchemyAutopilotRepository(session),
                clock=SystemClock(),
                queue=SqlQueueControl(session),
                dead_letters=SqlDeadLetterRuns(session),
            ),
        )
    )
    return _Panel(service=service, session=session)


Panel = Annotated[_Panel, Depends(_panel)]


@router.get(PATH_GENERATION_RUNS, response_model=QueueBoardResponse)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def get_queue_board(request: Request, panel: Panel) -> QueueBoardResponse:
    """The queue panel."""
    del request
    board = await panel.service.board()
    return QueueBoardResponse(
        active=[QueueItemResponse(**asdict(item)) for item in board.active],
        dead=[QueueItemResponse(**asdict(item)) for item in board.dead],
        backlog=[BacklogItemResponse(**asdict(item)) for item in board.backlog],
        average_drive_minutes=board.average_drive_minutes,
    )


async def _apply(panel: _Panel, outcome: str) -> QueueActionResponse:
    if outcome == OUTCOME_NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=outcome)
    if outcome != OUTCOME_DONE:
        await panel.session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=outcome)
    await panel.session.commit()
    return QueueActionResponse(outcome=outcome)


@router.post(PATH_GENERATION_RUN_RETRY, response_model=QueueActionResponse)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def retry_generation_run(
    request: Request, run_id: UUID, panel: Panel
) -> QueueActionResponse:
    """Put a dead-lettered autopilot run back in the queue."""
    del request
    return await _apply(panel, await panel.service.retry(run_id))


@router.post(PATH_GENERATION_RUN_DISCARD, response_model=QueueActionResponse)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def discard_generation_run(
    request: Request, run_id: UUID, panel: Panel
) -> QueueActionResponse:
    """Close a dead-lettered autopilot run."""
    del request
    return await _apply(panel, await panel.service.discard(run_id))


@router.post(PATH_GENERATION_RUN_CANCEL, response_model=QueueActionResponse)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def cancel_generation_run(
    request: Request, run_id: UUID, panel: Panel
) -> QueueActionResponse:
    """Take an autopilot run that has not started out of the queue."""
    del request
    return await _apply(panel, await panel.service.cancel(run_id))


@router.post(PATH_BACKLOG_GENERATE, response_model=QueueActionResponse)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def generate_backlog_theme(
    request: Request, candidate_id: UUID, panel: Panel
) -> QueueActionResponse:
    """Queue a backlog theme at once, outside the daily cap."""
    del request
    return await _apply(panel, await panel.service.generate_now(candidate_id))


__all__ = ["router"]
