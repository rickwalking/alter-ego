"""The owner Retry's one write, inside a savepoint of the request's session.

``apply`` runs the ``lock_version`` CAS and the ``in_progress`` flip through the
editorial ``claim_automation_phase`` (the pre-run checks the autopilot path
uses: in-progress guard, revision cap, CAS), brings a rejected carousel's
status back, stages the queued resume (dedupe key: project plus the new lock
version), and moves an escalated autopilot run back to ``generating``. A
reopen of a rejected final review runs the CAS and puts the review back in
front of the owner; nothing is staged. Any refusal raises inside the savepoint,
so it rolls back as one: no stage, no status change, no run move.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel import (
    CAROUSEL_STATUS_COMPLETED,
    CAROUSEL_STATUS_PENDING,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_RESUME_ALREADY_IN_PROGRESS,
    ERR_REVISION_CAP_EXCEEDED,
    PHASE_FINAL_REVIEW,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_REJECTED,
    REVIEW_ACTION_REVISE,
    RUN_ACTION_REDRIVE,
)
from rag_backend.domain.constants.content_feedback import (
    FEEDBACK_SOURCE_AUTOPILOT,
    STRUCTURED_FEEDBACK_SOURCE_KEY,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.editorial.public import (
    AutomationRun,
    CarouselProjectWriteOwner,
    EditorialWorkflowEngine,
    claim_automation_phase,
)
from rag_backend.modules.generation_queue.constants import REASON_OWNER_CAROUSEL_RETRY
from rag_backend.modules.generation_queue.domain.models import (
    WorkflowResumePayload,
    resume_stage,
)
from rag_backend.modules.generation_queue.domain.owner_retry import (
    OwnerRetryCommand,
    RetryFacts,
    RetryKind,
    RetryRefusal,
    escalated_run,
)
from rag_backend.modules.generation_queue.domain.owner_retry_ports import (
    RetryPlan,
    RetryWrite,
)
from rag_backend.modules.generation_queue.infrastructure.owner_retry_facts import (
    OwnerRetryFacts,
)
from rag_backend.modules.generation_queue.infrastructure.staging import (
    stage_generation_run,
)

_REFUSAL_BY_ERROR: dict[str, RetryRefusal] = {
    ERR_VERSION_CONFLICT: RetryRefusal.VERSION_CONFLICT,
    ERR_REVISION_CAP_EXCEEDED: RetryRefusal.REVISION_CAP_EXCEEDED,
    ERR_RESUME_ALREADY_IN_PROGRESS: RetryRefusal.RUN_IN_PROGRESS,
}


class RetryRefusedError(Exception):
    """Raised inside the savepoint so a lost write rolls back as one."""

    def __init__(self, refusal: RetryRefusal) -> None:
        super().__init__(refusal.value)
        self.refusal = refusal


class SqlOwnerRetryStore:
    """Implement the Retry store without owning the request session."""

    def __init__(self, session: AsyncSession, engine: EditorialWorkflowEngine) -> None:
        self._session = session
        self._engine = engine
        self._facts = OwnerRetryFacts(session, engine)

    async def read(self, command: OwnerRetryCommand) -> RetryFacts | None:
        """Lock the carousel row and gather the facts."""
        return await self._facts.read(command)

    async def apply(self, plan: RetryPlan) -> RetryWrite:
        """Write the Retry in a savepoint; a refusal leaves nothing behind."""
        try:
            async with self._session.begin_nested():
                return await self._write(plan)
        except RetryRefusedError as exc:
            return RetryWrite(refusal=exc.refusal)
        except ValueError as exc:
            refusal = _REFUSAL_BY_ERROR.get(str(exc))
            if refusal is None:
                raise
            return RetryWrite(refusal=refusal)

    async def commit(self) -> None:
        """Commit the Retry and its audit together."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Roll back a refused Retry and release the row lock."""
        await self._session.rollback()

    async def _write(self, plan: RetryPlan) -> RetryWrite:
        if plan.kind is RetryKind.REOPEN:
            write = await self._reopen(plan)
        else:
            write = await self._rerun(plan)
        return await self._revive(plan, write)

    async def _reopen(self, plan: RetryPlan) -> RetryWrite:
        """Put a rejected final review back in front of the owner."""
        owner = CarouselProjectWriteOwner(self._session)
        version = await owner.bump_resume_lock_version(
            plan.command.project_id, _expected(plan)
        )
        await owner.reopen_final_review(plan.command.project_id)
        await owner.restore_active_status(
            plan.command.project_id, CAROUSEL_STATUS_COMPLETED
        )
        return RetryWrite(
            lock_version=version,
            phase=PHASE_FINAL_REVIEW,
            phase_status=PHASE_STATUS_AWAITING_HUMAN,
        )

    async def _rerun(self, plan: RetryPlan) -> RetryWrite:
        """Claim the run start, then stage the re-drive or the revise."""
        action = _ACTION_BY_KIND[plan.kind]
        claim = await claim_automation_phase(self._automation_run(plan, action))
        if plan.facts.carousel.phase_status == PHASE_STATUS_REJECTED:
            await CarouselProjectWriteOwner(self._session).restore_active_status(
                plan.command.project_id, CAROUSEL_STATUS_PENDING
            )
        payload = WorkflowResumePayload(
            project_id=plan.command.project_id,
            action=action,
            reviewer_id=plan.command.actor_id,
            feedback=plan.feedback or None,
            project_title=claim.topic,
            structured_feedback=_structured(plan),
        )
        staged = await stage_generation_run(
            self._session, resume_stage(payload, claim.lock_version)
        )
        if not staged:
            raise RetryRefusedError(RetryRefusal.CONCURRENT_UPDATE)
        return RetryWrite(
            lock_version=claim.lock_version,
            phase=plan.facts.carousel.phase,
            phase_status=PHASE_STATUS_IN_PROGRESS,
        )

    def _automation_run(self, plan: RetryPlan, action: str) -> AutomationRun:
        return AutomationRun(
            engine=self._engine,
            session=self._session,
            project_id=plan.command.project_id,
            expected_version=_expected(plan),
            action=action,
            reviewer_id=plan.command.actor_id,
            feedback=plan.feedback,
            structured_feedback=_structured(plan),
        )

    async def _revive(self, plan: RetryPlan, write: RetryWrite) -> RetryWrite:
        """Move an escalated autopilot run back to generating (a CAS)."""
        run = escalated_run(plan.facts)
        if run is None:
            return write
        moved = await SqlAlchemyAutopilotRepository(self._session).transition(
            TransitionCommand(
                run_id=run.run_id,
                expected=AutopilotRunState.ESCALATED,
                new=AutopilotRunState.GENERATING,
                reason=REASON_OWNER_CAROUSEL_RETRY,
            )
        )
        if not moved:
            raise RetryRefusedError(RetryRefusal.CONCURRENT_UPDATE)
        return RetryWrite(
            lock_version=write.lock_version,
            phase=write.phase,
            phase_status=write.phase_status,
            autopilot_run_id=run.run_id,
        )


_ACTION_BY_KIND: dict[RetryKind, str] = {
    RetryKind.REDRIVE: RUN_ACTION_REDRIVE,
    RetryKind.REVISE: REVIEW_ACTION_REVISE,
}


def _expected(plan: RetryPlan) -> int:
    """The website's expected version; Telegram's is the one read under the lock."""
    expected = plan.command.expected_version
    if expected is None:
        return plan.facts.carousel.lock_version
    return expected


def _structured(plan: RetryPlan) -> dict[str, object] | None:
    """Tag the system feedback line so it is applied once and never re-fed."""
    if not plan.feedback:
        return None
    return {STRUCTURED_FEEDBACK_SOURCE_KEY: FEEDBACK_SOURCE_AUTOPILOT}


__all__ = ["RetryRefusedError", "SqlOwnerRetryStore"]
