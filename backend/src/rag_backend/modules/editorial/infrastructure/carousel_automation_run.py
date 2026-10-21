"""Run one unattended phase the way the HTTP resume does.

The autopilot tick used to call the engine resume on its own session. The
lock bump stayed uncommitted for the whole LLM run, the row never showed
``in_progress`` (no ``run_started_at``, no heartbeat), and any failure rolled
the row back while the checkpointer had already committed the approved gate.
The workflow was then parked before the next node and nothing ever ran it.

Here the caller's session does only the pre-run steps: the in-progress
guard, the revision-cap check, the ``lock_version`` CAS, and the
``in_progress`` flip. It commits them, then the phase runs through the same
run-owned wrapper the HTTP route schedules (epoch fence, heartbeat loop,
run events, its own session, failure marking). The caller awaits it inline,
so the tick still learns the outcome, but no transaction stays open across
the LLM work.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_workflow import (
    ERR_NOTHING_TO_REDRIVE,
    ERR_RESUME_ALREADY_IN_PROGRESS,
    PHASE_STATUS_IN_PROGRESS,
    REVIEW_ACTION_REVISE,
    RUN_ACTION_REDRIVE,
)
from rag_backend.modules.editorial.infrastructure.carousel_automation import (
    EditorialWorkflowEngine,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_write_owner import (
    CarouselProjectWriteOwner,
)


@dataclass(frozen=True, kw_only=True)
class AutomationRun:
    """One unattended approve, revise, or re-drive at a known lock version."""

    engine: EditorialWorkflowEngine
    session: AsyncSession
    project_id: str
    expected_version: int
    action: str
    reviewer_id: str = ""
    feedback: str = ""
    structured_feedback: Mapping[str, object] | None = None


@dataclass(frozen=True, kw_only=True)
class _RowFacts:
    phase_status: str
    topic: str


async def run_automation_phase(run: AutomationRun) -> None:
    """Commit the run start, then run the phase inline with run ownership.

    Raises ``ValueError`` before any work: ``resume_already_in_progress``
    when a run is in flight, ``version_conflict`` when the CAS loses, and
    ``revision_cap_exceeded`` for a revise over the cap. A failure inside the
    phase does not raise: the run wrapper marks the row ``failed`` and
    publishes ``run.finished``, as for the HTTP resume.
    """
    from rag_backend.application.services.carousel import (
        editorial_workflow_resume_runner as resume_runner,
    )

    facts = await _row_facts(run.session, run.project_id)
    if facts.phase_status == PHASE_STATUS_IN_PROGRESS:
        raise ValueError(ERR_RESUME_ALREADY_IN_PROGRESS)
    await _ensure_revision_room(run, facts.topic)
    owner = CarouselProjectWriteOwner(run.session)
    await owner.bump_resume_lock_version(run.project_id, run.expected_version)
    await run.engine.mark_resume_in_progress(run.project_id, run.session)
    await owner.commit()
    await resume_runner.execute_resume_run(
        run.engine,
        resume_runner.BackgroundResumeParams(
            project_id=run.project_id,
            action=run.action,
            reviewer_id=run.reviewer_id,
            feedback=run.feedback or None,
            project_title=facts.topic,
            structured_feedback=_structured(run.structured_feedback),
        ),
    )


async def redrive_automation_phase(run: AutomationRun) -> None:
    """Re-run a parked pending node through the same run-owned path.

    ``run.action`` is ignored: a re-drive never sends a review decision, so
    the re-run phase parks at its own gate for the next review. Raises
    ``nothing_to_redrive`` before any write when no node is parked.
    """
    if not await run.engine.is_parked_before_node(run.project_id):
        raise ValueError(ERR_NOTHING_TO_REDRIVE)
    await run_automation_phase(
        AutomationRun(
            engine=run.engine,
            session=run.session,
            project_id=run.project_id,
            expected_version=run.expected_version,
            action=RUN_ACTION_REDRIVE,
        )
    )


async def _row_facts(session: AsyncSession, project_id: str) -> _RowFacts:
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    result = await session.execute(
        select(CarouselProjectModel.phase_status, CarouselProjectModel.topic).where(
            CarouselProjectModel.id == project_id
        )
    )
    row = result.one_or_none()
    if row is None:
        return _RowFacts(phase_status="", topic="")
    return _RowFacts(phase_status=str(row[0] or ""), topic=str(row[1] or ""))


async def _ensure_revision_room(run: AutomationRun, title: str) -> None:
    """Refuse a capped revise BEFORE the row is marked ``in_progress``."""
    if run.action != REVIEW_ACTION_REVISE:
        return
    prior = await run.engine.get_workflow_state(run.project_id)
    if prior is None:
        return
    from rag_backend.application.services.carousel import (
        editorial_workflow_service_helpers as engine_checks,
    )
    from rag_backend.application.services.notification_service import (
        NotificationService,
    )

    await engine_checks.validate_revision_cap(
        prior,
        engine_checks.RevisionCapValidationContext(
            project_id=run.project_id,
            project_title=title,
            db=run.session,
            notifications=NotificationService(),
            structured_feedback=_structured(run.structured_feedback),
        ),
    )


def _structured(
    raw: Mapping[str, object] | None,
) -> dict[str, object] | None:
    if raw is None:
        return None
    return dict(raw)


__all__ = [
    "AutomationRun",
    "redrive_automation_phase",
    "run_automation_phase",
]
