"""Background execution for async editorial workflow resume (RW-010-RW-013).

AE-0315: the background task is a *run-owned* execution context — it captures
the row's ``run_epoch`` into the ``carousel_run_epoch`` contextvar at start
(fencing every ORM flush, checkpoint commit, and raw-SQL site against a
reaper flip), heartbeats ``run_heartbeat_at`` on a fixed interval and at
stage boundaries, emits the coarse ``run.stage_changed`` stages
(generating → validating → persisting), and closes the run with
``run.finished`` on every exit path. A fenced (reaped) zombie logs and stops:
the reaper already owns the row and has published ``run.finished(stale)``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog

from rag_backend.application.services.carousel.editorial_workflow_run_events import (
    publish_run_finished,
    publish_run_stage_changed,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    ResumeWorkflowInput,
    publish_workflow_sse_updates,
    resolve_background_resume_sse_error_message,
)
from rag_backend.domain.constants.carousel_run import (
    DEFAULT_RUN_HEARTBEAT_INTERVAL_SECONDS,
    LOG_EVENT_RUN_FENCED,
    RUN_FINISHED_REASON_COMPLETED,
    RUN_FINISHED_REASON_FAILED,
    RUN_STAGE_GENERATING,
    RUN_STAGE_PERSISTING,
    RUN_STAGE_VALIDATING,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_BACKGROUND_RESUME_FAILED,
    ERR_BACKGROUND_RESUME_STUCK,
    ERR_PERSONA_SCORE_TOO_LOW,
    ERR_REVISION_CAP_EXCEEDED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    REVIEW_ACTION_APPROVE,
)
from rag_backend.domain.models.carousel_run import (
    CarouselRunContext,
    StaleRunEpochError,
    carousel_run_epoch_var,
)
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.modules.editorial.public import (
    CarouselProjectWriteOwner,
    read_run_fence,
    write_run_heartbeat_once,
    write_run_heartbeat_with_retry,
)

logger = structlog.get_logger()

_background_tasks: set[asyncio.Task[None]] = set()

_TASK_NAME_PREFIX = "workflow-resume-"


@dataclass(frozen=True)
class _MarkFailedParams:
    """Inputs for marking a background resume as failed."""

    service: EditorialWorkflowService
    project_id: str
    message: str
    recoverable: bool


@dataclass(frozen=True)
class BackgroundResumeParams:
    """Inputs required to resume a workflow in the background."""

    project_id: str
    action: str
    reviewer_id: str
    feedback: str | None
    project_title: str
    structured_feedback: dict[str, object] | None


def schedule_background_resume(
    service: EditorialWorkflowService,
    params: BackgroundResumeParams,
) -> None:
    """Fire-and-forget background resume with task tracking."""
    task = asyncio.create_task(
        _execute_background_resume(service, params),
        name=f"{_TASK_NAME_PREFIX}{params.project_id}",
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def cancel_background_resume_task(project_id: str) -> bool:
    """Best-effort cancel of an in-process resume task by reference.

    Called by the stale-run reaper when the dying task's asyncio handle is
    still known in this process; the epoch fence is the correctness
    guarantee — cancellation just stops wasted LLM spend.
    """
    name = f"{_TASK_NAME_PREFIX}{project_id}"
    cancelled = False
    for task in _background_tasks:
        if task.get_name() == name and not task.done():
            task.cancel()
            cancelled = True
    return cancelled


async def _run_heartbeat_loop(ctx: CarouselRunContext) -> None:
    """Heartbeat run_heartbeat_at until cancelled or the fence is lost.

    The interval is the domain default (60s); the write itself retries on
    transient failure and is self-fencing (epoch pinned in its WHERE clause).
    """
    while True:
        await asyncio.sleep(DEFAULT_RUN_HEARTBEAT_INTERVAL_SECONDS)
        if not await write_run_heartbeat_with_retry(ctx.project_id, ctx.epoch):
            return


async def _execute_background_resume(
    service: EditorialWorkflowService,
    params: BackgroundResumeParams,
) -> None:
    """Run-owned wrapper: fence capture, heartbeat task, fenced-zombie exit."""
    fence = await read_run_fence(params.project_id)
    token = carousel_run_epoch_var.set(fence) if fence is not None else None
    heartbeat = (
        asyncio.create_task(_run_heartbeat_loop(fence)) if fence is not None else None
    )
    try:
        await _run_background_resume(service, params)
    except StaleRunEpochError:
        # Reaped mid-flight: the reaper owns the row (epoch bumped), already
        # published run.finished(stale), and the replacement run is free to
        # start. This zombie must not touch anything else.
        logger.warning(LOG_EVENT_RUN_FENCED, project_id=params.project_id)
    finally:
        if heartbeat is not None:
            heartbeat.cancel()
        if token is not None:
            carousel_run_epoch_var.reset(token)


async def _beat_and_stage(ctx: CarouselRunContext | None, stage: str) -> None:
    """Emit a stage boundary and refresh the heartbeat alongside it.

    AE-0320: this is awaited INLINE by the run's main coroutine, whose session
    may hold flushed-but-uncommitted writes on the same row — the beat must be
    single-attempt and lock-timeout-bounded (soft-fail) or it self-deadlocks
    the run (prod incident 2026-07-18). Liveness is owned by the interval
    heartbeat loop; a skipped stage beat is cosmetic.
    """
    if ctx is None:
        return
    await publish_run_stage_changed(ctx.project_id, stage)
    await write_run_heartbeat_once(ctx.project_id, ctx.epoch)


async def _run_background_resume(
    service: EditorialWorkflowService,
    params: BackgroundResumeParams,
) -> None:
    session_factory = get_session_maker()
    ctx = carousel_run_epoch_var.get()
    async with session_factory() as db:
        try:
            prior_state = await service.get_workflow_state(params.project_id)
            prior_phase = (
                str(prior_state.get("current_phase", "")) if prior_state else ""
            )
            await _beat_and_stage(ctx, RUN_STAGE_GENERATING)

            state = await service.resume_workflow(
                ResumeWorkflowInput(
                    project_id=params.project_id,
                    action=params.action,
                    reviewer_id=params.reviewer_id,
                    feedback=params.feedback,
                    db=db,
                    persona=None,
                    project_title=params.project_title,
                    structured_feedback=params.structured_feedback,
                ),
            )
            await _beat_and_stage(ctx, RUN_STAGE_VALIDATING)

            if _detect_resume_stuck(
                params,
                prior_phase,
                state,
            ):
                logger.warning(
                    "background_resume_stuck",
                    project_id=params.project_id,
                    phase=prior_phase,
                    action=params.action,
                )
                await _revert_background_resume_stuck(
                    service,
                    params.project_id,
                    prior_phase,
                )
                return

            await _beat_and_stage(ctx, RUN_STAGE_PERSISTING)
            await CarouselProjectWriteOwner(db).commit()
            await publish_workflow_sse_updates(params.project_id, state)
            await publish_run_finished(
                params.project_id,
                RUN_FINISHED_REASON_COMPLETED,
                final_phase_status=str(state.get("phase_status", "")),
            )
        except StaleRunEpochError:
            await db.rollback()
            raise
        except ValueError as exc:
            await db.rollback()
            detail = resolve_background_resume_sse_error_message(str(exc))
            if detail in {
                ERR_REVISION_CAP_EXCEEDED,
                ERR_PERSONA_SCORE_TOO_LOW,
            }:
                logger.warning(
                    "background_resume_validation_failed",
                    project_id=params.project_id,
                    detail=detail,
                )
            await _mark_background_resume_failed(
                _MarkFailedParams(
                    service=service,
                    project_id=params.project_id,
                    message=detail,
                    recoverable=detail != ERR_REVISION_CAP_EXCEEDED,
                ),
            )
        except asyncio.CancelledError:
            # AE-0209: a cancelled background task (e.g. shutdown/kill) must not
            # leave the workflow holding the in_progress lock. ``CancelledError``
            # is a BaseException, so the generic ``except Exception`` below never
            # catches it — release the lock (mark failed/recoverable) then
            # re-raise to honor cooperative cancellation. AE-0315: when the
            # cancel came from the reaper the epoch is already fenced — the
            # mark-failed write is rejected and skipped (the reaper owns the
            # row and published run.finished(stale)).
            await db.rollback()
            logger.warning(
                "background_resume_cancelled",
                project_id=params.project_id,
            )
            try:
                await _mark_background_resume_failed(
                    _MarkFailedParams(
                        service=service,
                        project_id=params.project_id,
                        message=ERR_BACKGROUND_RESUME_FAILED,
                        recoverable=True,
                    ),
                )
            except StaleRunEpochError:
                logger.warning(LOG_EVENT_RUN_FENCED, project_id=params.project_id)
            raise
        except Exception as exc:
            await db.rollback()
            logger.exception(
                "background_resume_failed",
                project_id=params.project_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            await _mark_background_resume_failed(
                _MarkFailedParams(
                    service=service,
                    project_id=params.project_id,
                    message=ERR_BACKGROUND_RESUME_FAILED,
                    recoverable=True,
                ),
            )


def _detect_resume_stuck(
    params: BackgroundResumeParams,
    prior_phase: str,
    state: dict[str, object],
) -> bool:
    """Return True when an approve resume completed but phase did not advance.

    Revise and reject actions legitimately return to the same phase with
    awaiting_human — stuck detection is scoped to approve only.
    """
    if params.action != REVIEW_ACTION_APPROVE:
        return False
    current_phase = str(state.get("current_phase", ""))
    current_status = str(state.get("phase_status", ""))
    return bool(
        prior_phase
        and current_phase == prior_phase
        and current_status == PHASE_STATUS_AWAITING_HUMAN
    )


async def _revert_background_resume_stuck(
    service: EditorialWorkflowService,
    project_id: str,
    _prior_phase: str,
) -> None:
    """Revert DB phase_status to awaiting_human and publish error SSE."""
    session_factory = get_session_maker()
    async with session_factory() as db:
        await CarouselProjectWriteOwner(db).set_phase_status_and_commit(
            project_id,
            PHASE_STATUS_AWAITING_HUMAN,
        )
        await service.publish_resume_error_event(
            project_id,
            message=ERR_BACKGROUND_RESUME_STUCK,
            recoverable=True,
        )
        await publish_run_finished(
            project_id,
            RUN_FINISHED_REASON_FAILED,
            final_phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )


async def _mark_background_resume_failed(
    params: _MarkFailedParams,
) -> None:
    session_factory = get_session_maker()
    async with session_factory() as db:
        await CarouselProjectWriteOwner(db).set_phase_status_and_commit(
            params.project_id,
            PHASE_STATUS_FAILED,
        )
        await params.service.publish_resume_error_event(
            params.project_id,
            message=params.message,
            recoverable=params.recoverable,
        )
        await publish_run_finished(
            params.project_id,
            RUN_FINISHED_REASON_FAILED,
            final_phase_status=PHASE_STATUS_FAILED,
        )


__all__ = [
    "BackgroundResumeParams",
    "cancel_background_resume_task",
    "schedule_background_resume",
]
