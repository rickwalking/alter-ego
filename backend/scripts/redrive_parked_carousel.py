"""One-shot ops: re-drive a carousel parked before its next node (AE-0363).

WHY THIS EXISTS
---------------
Before AE-0363 the autopilot approved a gate inside the worker tick. When the
next phase failed (a provider timeout, a crash, a restart), the checkpointer
had already committed the approved gate but the tick rolled the row back. The
workflow was left parked: checkpoint ``<next phase>/approved`` with that node
pending and no interrupt, row still at the old gate, no run in flight. Prod
carousel ``8e350d6e-78fc-436c-ab95-bed02535198b`` (autopilot run
``9e06e958-45b6-4339-bcb2-92981d4e4e7b``) is stuck like that at ``content``.

After the AE-0363 deploy the autopilot re-drives such a carousel by itself on
the first tick after the 10-minute grace period. Use this script to check the
state first, or to re-drive at once when the autopilot worker is disabled.

WHAT IT DOES
------------
Default (dry run): prints the row, the checkpoint, and whether a re-drive is
possible. Writes nothing.

``--apply``: runs the AE-0363 facade operation ``redrive_automation_phase``,
the same path the autopilot uses: lock-version CAS, row flipped to
``in_progress`` (run_started_at and heartbeat set) and committed, then the
pending node runs under the run wrapper (epoch fence, heartbeat loop,
``run.finished``). It sends NO review decision: the re-run phase parks at its
own gate and the autopilot policy checks it on the next tick.

SAFETY
------
Refuses when the checkpoint has no parked node (nothing pending, a human gate
open, or an approved-hold carousel) or when a run is in flight. A concurrent
autopilot re-drive loses the CAS or sees the run in flight, so the phase never
runs twice. A phase failure marks the row ``failed``; the autopilot then
escalates the run with a Telegram notice.

USAGE (inside the backend container, AFTER the AE-0363 deploy)
    docker compose exec backend uv run python \\
        scripts/redrive_parked_carousel.py <project_id>            # dry run
    docker compose exec backend uv run python \\
        scripts/redrive_parked_carousel.py <project_id> --apply    # re-drive
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass

from rag_backend.agents.harness import build_checkpointer
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.bootstrap.autopilot_worker_factory import autopilot_engine_factory
from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import (
    close_db,
    get_session_maker,
    init_db,
)
from rag_backend.infrastructure.database.models import CarouselProjectModel
from rag_backend.infrastructure.logging import setup_logging
from rag_backend.modules.editorial.public import (
    AutomationRun,
    redrive_automation_phase,
)

_APPLY_FLAG = "--apply"
_EXIT_OK = 0
_EXIT_USAGE = 2
_EXIT_REFUSED = 3
_ARGC_DRY_RUN = 2
_ARGC_APPLY = 3


@dataclass(frozen=True)
class _Request:
    project_id: str
    apply: bool


async def _describe(service: EditorialWorkflowService, project_id: str) -> str:
    state = await service.get_workflow_state(project_id) or {}
    drafts = state.get("slide_drafts") or []
    return (
        f"checkpoint phase={state.get('current_phase')} "
        f"status={state.get('phase_status')} "
        f"slide_drafts={len(drafts) if isinstance(drafts, list) else 0} "
        f"content_approved={bool(state.get('content_approved'))}"
    )


def _row_line(row: CarouselProjectModel) -> str:
    return (
        f"row phase={row.current_phase} status={row.phase_status} "
        f"lock_version={row.lock_version} run_started_at={row.run_started_at} "
        f"run_heartbeat_at={row.run_heartbeat_at} updated_at={row.updated_at}"
    )


async def _redrive(service: EditorialWorkflowService, request: _Request) -> int:
    async with get_session_maker()() as session:
        row = await session.get(CarouselProjectModel, request.project_id)
        if row is None:
            print("REFUSED: no carousel with that id.")
            return _EXIT_REFUSED
        print(f"BEFORE: {_row_line(row)}")
        print(f"BEFORE: {await _describe(service, request.project_id)}")
        parked = await service.is_parked_before_node(request.project_id)
        running = str(row.phase_status) == PHASE_STATUS_IN_PROGRESS
        print(f"parked_before_node={parked} run_in_flight={running}")
        if not parked or running:
            print("REFUSED: nothing to re-drive (not parked, or a run is in flight).")
            return _EXIT_REFUSED
        if not request.apply:
            print(f"DRY RUN: re-run with {_APPLY_FLAG} to re-drive the pending node.")
            return _EXIT_OK
        await redrive_automation_phase(
            AutomationRun(
                engine=service,
                session=session,
                project_id=request.project_id,
                expected_version=int(row.lock_version),
                action="",
            )
        )
    async with get_session_maker()() as fresh:
        after = await fresh.get(CarouselProjectModel, request.project_id)
        if after is not None:
            print(f"AFTER:  {_row_line(after)}")
    print(f"AFTER:  {await _describe(service, request.project_id)}")
    return _EXIT_OK


async def run(request: _Request) -> int:
    """Open the DB and the durable checkpointer, then inspect or re-drive."""
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
                print("REFUSED: no durable checkpointer is configured.")
                return _EXIT_REFUSED
            service = autopilot_engine_factory(checkpointer)()
            return await _redrive(service, request)
    finally:
        await close_db()


def _parse(argv: list[str]) -> _Request | None:
    if len(argv) == _ARGC_DRY_RUN:
        return _Request(project_id=argv[1], apply=False)
    if len(argv) == _ARGC_APPLY and argv[2] == _APPLY_FLAG:
        return _Request(project_id=argv[1], apply=True)
    return None


def main() -> int:
    """Entry point. Dry run unless ``--apply`` is given."""
    request = _parse(sys.argv)
    if request is None:
        print(f"usage: {sys.argv[0]} <project_id> [{_APPLY_FLAG}]", file=sys.stderr)
        return _EXIT_USAGE
    return asyncio.run(run(request))


if __name__ == "__main__":
    raise SystemExit(main())
