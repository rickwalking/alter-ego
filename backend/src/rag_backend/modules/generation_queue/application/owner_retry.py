"""The owner's carousel Retry: decide under the row lock, write once, audit.

One transaction, in this order: lock the carousel row and read the facts,
decide, then the store's savepoint runs the ``lock_version`` CAS, the
``in_progress`` flip, the queued resume stage and the escalated autopilot run's
move back to ``generating``; the audit event follows on the same session and
everything commits together. Any refusal rolls all of it back, so a refused
Retry leaves no stage, no audit and no run move. Refusals are only logged.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from rag_backend.modules.generation_queue.application.owner_retry_feedback import (
    retry_feedback,
)
from rag_backend.modules.generation_queue.constants import (
    LOG_RETRY_ACCEPTED,
    LOG_RETRY_ANNOUNCE_FAILED,
    LOG_RETRY_REFUSED,
)
from rag_backend.modules.generation_queue.domain.owner_retry import (
    OwnerRetryCommand,
    RetryDecision,
    RetryFacts,
    RetryKind,
    RetryRefusal,
    decide_retry,
)
from rag_backend.modules.generation_queue.domain.owner_retry_ports import (
    OwnerRetryAudit,
    OwnerRetryStore,
    RetryAuditCommand,
    RetryCapability,
    RetryPlan,
    RetryRefusedError,
    RetryResult,
    RetryWrite,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class OwnerRetryDependencies:
    """The store and the audit, bound to one session."""

    store: OwnerRetryStore
    audit: OwnerRetryAudit


class OwnerRetryService:
    """Run one owner Retry; the website owns its transaction, Telegram does not."""

    def __init__(
        self, deps: OwnerRetryDependencies, *, owns_transaction: bool = True
    ) -> None:
        self._deps = deps
        self._owns_transaction = owns_transaction

    async def retry(self, command: OwnerRetryCommand) -> RetryResult:
        """Accept and stage one Retry, or refuse it with nothing changed."""
        try:
            facts = await self._deps.store.read(command)
        except RetryRefusedError as exc:
            return await self._refused(command, exc.refusal)
        if facts is None:
            return await self._refused(command, RetryRefusal.NOT_FOUND)
        decision = decide_retry(facts)
        plan = _plan(command, facts, decision)
        if plan is None:
            return await self._refused(command, _refusal(decision))
        write = await self._deps.store.apply(plan)
        if write.refusal is not None:
            return await self._refused(command, write.refusal)
        await self._deps.audit.record(RetryAuditCommand(plan=plan, write=write))
        return await self._accept(plan, write)

    async def inspect(self, command: OwnerRetryCommand) -> RetryCapability:
        """Whether a Retry would be accepted now; nothing is written."""
        try:
            facts = await self._deps.store.read(command)
        except RetryRefusedError as exc:
            await self._rollback()
            return RetryCapability(can_retry=False, refusal=exc.refusal)
        await self._rollback()
        if facts is None:
            return RetryCapability(can_retry=False, refusal=RetryRefusal.NOT_FOUND)
        decision = decide_retry(facts)
        return RetryCapability(
            can_retry=decision.kind is not None,
            kind=decision.kind,
            refusal=decision.refusal,
            lock_version=facts.carousel.lock_version,
        )

    async def announce(self, result: RetryResult, project_id: str) -> None:
        """Push the run start to the browser; call only after the commit.

        Best effort: the Retry already committed, so a failure here (the row
        re-read, the event bus) is logged with its error class and swallowed;
        it never blocks the caller's replies.
        """
        if not result.starts_run:
            return
        try:
            await self._deps.store.announce(project_id, result.phase)
        except Exception as exc:
            logger.warning(
                LOG_RETRY_ANNOUNCE_FAILED,
                project_id=project_id,
                error=type(exc).__name__,
            )

    async def _accept(self, plan: RetryPlan, write: RetryWrite) -> RetryResult:
        """Commit when the transaction is ours, then announce the run start."""
        command = plan.command
        await self._commit()
        logger.info(
            LOG_RETRY_ACCEPTED,
            project_id=command.project_id,
            surface=command.surface.value,
            retry_kind=plan.kind.value,
        )
        result = _accepted(plan, write)
        if self._owns_transaction:
            await self.announce(result, command.project_id)
        return result

    async def _refused(
        self, command: OwnerRetryCommand, refusal: RetryRefusal
    ) -> RetryResult:
        await self._rollback()
        logger.info(
            LOG_RETRY_REFUSED,
            project_id=command.project_id,
            surface=command.surface.value,
            refusal=refusal.value,
        )
        return RetryResult(accepted=False, refusal=refusal)

    async def _commit(self) -> None:
        if self._owns_transaction:
            await self._deps.store.commit()

    async def _rollback(self) -> None:
        if self._owns_transaction:
            await self._deps.store.rollback()


def _plan(
    command: OwnerRetryCommand, facts: RetryFacts, decision: RetryDecision
) -> RetryPlan | None:
    """The accepted plan; a revise carries the system feedback line."""
    kind = decision.kind
    if kind is None:
        return None
    feedback = ""
    if kind is RetryKind.REVISE:
        feedback = retry_feedback(facts, decision.reason)
    return RetryPlan(
        command=command,
        facts=facts,
        kind=kind,
        reason=decision.reason,
        feedback=feedback,
    )


def _refusal(decision: RetryDecision) -> RetryRefusal:
    return decision.refusal or RetryRefusal.NOT_RETRYABLE


def _accepted(plan: RetryPlan, write: RetryWrite) -> RetryResult:
    return RetryResult(
        accepted=True,
        kind=plan.kind,
        phase=write.phase,
        phase_status=write.phase_status,
        lock_version=write.lock_version,
        autopilot_run_id=write.autopilot_run_id,
    )


__all__ = ["OwnerRetryDependencies", "OwnerRetryService"]
