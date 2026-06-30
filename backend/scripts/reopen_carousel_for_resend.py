"""One-shot ops: reopen an already-approved (terminated) carousel so it can be
sent back to an earlier phase via the normal /workflow/resume API (AE-0288).

WHY THIS EXISTS
---------------
The AE-0288 ``approved_hold`` fix keeps carousels approved AFTER deploy parked at
a resumable interrupt. Carousels that were approved BEFORE the fix shipped have a
TERMINATED LangGraph thread (``snapshot.next == ()``) that the resume API cannot
re-enter. This script does the single direct checkpointer operation that puts
such a thread back at a genuine ``final_review`` pause (``awaiting_human``) with
the publish lock dropped, after which a normal API send-back
(``revise`` + ``structured_feedback.target_phase``) regenerates the targeted
phase while reusing existing images.

SAFETY
------
Refuses to touch any thread that is not BOTH terminated (no pending node) AND
``workflow_status == approved_for_publish``. It never deletes data; it only
re-opens the final-review gate and marks the project row as in-review (draft) so
the carousel cannot be published while it is being re-reviewed. Idempotent: a
thread already paused at ``final_review`` is reported and left unchanged.

USAGE (run inside the backend container, AFTER the AE-0288 deploy)
    docker compose exec backend uv run python \
        scripts/reopen_carousel_for_resend.py <project_id>
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import AsyncExitStack
from typing import cast

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.agents.harness import build_checkpointer
from rag_backend.domain.constants.carousel_workflow import (
    CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING_HUMAN,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import (
    close_db,
    get_session_maker,
    init_db,
)
from rag_backend.infrastructure.database.models import CarouselProjectModel
from rag_backend.infrastructure.logging import get_logger, setup_logging

logger = get_logger()

_REOPEN_ACTION = "reopen_for_resend"
_EXPECTED_ARGC = 2
_EXIT_OK = 0
_EXIT_USAGE = 2
_EXIT_NOT_ELIGIBLE = 3


def _summarize(snapshot: object) -> str:
    values = getattr(snapshot, "values", {}) or {}
    pending = getattr(snapshot, "next", ()) or ()
    return (
        f"next={pending} current_phase={values.get('current_phase')!r} "
        f"phase_status={values.get('phase_status')!r} "
        f"workflow_status={values.get('workflow_status')!r} "
        f"quality_passed={values.get('quality_passed')!r}"
    )


def _is_terminated_and_approved(snapshot: object) -> bool:
    values = getattr(snapshot, "values", {}) or {}
    pending = getattr(snapshot, "next", ()) or ()
    approved = str(values.get("workflow_status", "")) == (
        WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
    )
    return not pending and approved


async def _sync_project_row_to_review(project_id: str) -> None:
    """Mark the DB row in-review/draft so it cannot be published while re-reviewed."""
    async with get_session_maker()() as session:
        project = await session.get(CarouselProjectModel, project_id)
        if project is None:
            logger.warning("reopen_project_row_missing", project_id=project_id)
            return
        project.current_phase = PHASE_FINAL_REVIEW
        project.phase_status = PHASE_STATUS_AWAITING_HUMAN
        project.workflow_status = CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT
        await session.commit()


async def reopen(project_id: str) -> int:
    settings = get_settings()
    setup_logging(debug=settings.debug)
    await init_db(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    try:
        async with AsyncExitStack() as stack:
            checkpointer = await build_checkpointer(settings, stack)
            if checkpointer is None:
                logger.error("reopen_no_durable_checkpointer")
                return _EXIT_NOT_ELIGIBLE
            engine = CarouselWorkflowEngine(checkpointer=checkpointer)
            config = cast(RunnableConfig, engine._run_config(project_id))
            before = await engine._app.aget_state(config)
            print(f"BEFORE: {_summarize(before)}")

            if not _is_terminated_and_approved(before):
                print(
                    "REFUSED: thread is not terminated+approved_for_publish; "
                    "nothing to reopen (a carousel still in the workflow is sent "
                    "back via the API directly)."
                )
                return _EXIT_NOT_ELIGIBLE

            await engine._app.ainvoke(
                Command(
                    goto=PHASE_FINAL_REVIEW,
                    resume={"action": _REOPEN_ACTION},
                    update={
                        "workflow_status": CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT,
                        "quality_passed": False,
                    },
                ),
                config=config,
            )
            after = await engine._app.aget_state(config)
            print(f"AFTER:  {_summarize(after)}")

        await _sync_project_row_to_review(project_id)
        print(
            "OK: reopened at final_review (awaiting_human, draft). Send it back "
            "to content via POST /api/carousels/<id>/workflow/resume "
            '{"action":"revise","structured_feedback":{"target_phase":"content"},'
            '"feedback":"...","expected_version":<lock>}'
        )
        return _EXIT_OK
    finally:
        await close_db()


def main() -> int:
    if len(sys.argv) != _EXPECTED_ARGC:
        print(f"usage: {sys.argv[0]} <project_id>", file=sys.stderr)
        return _EXIT_USAGE
    return asyncio.run(reopen(sys.argv[1]))


if __name__ == "__main__":
    raise SystemExit(main())
