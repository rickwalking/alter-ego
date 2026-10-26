"""Idempotent manual recovery orchestration with post-commit notification."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from rag_backend.modules.generation_queue.domain.errors import DriveLockBusyError
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    AuditCommand,
    MaintenanceNotice,
    ManualReprocessCommand,
    RecoveryCapability,
    RecoveryDecision,
    RecoveryMutation,
    RecoveryOutcome,
    RecoveryPolicy,
    RecoveryResult,
    RecoverySnapshot,
    RecoveryWrite,
    RefusalCode,
    StuckKind,
    WriteStatus,
    manual_stuck_kind,
    recovery_lock_keys,
)
from rag_backend.modules.generation_queue.domain.manual_recovery_classifier import (
    classify_recovery,
)
from rag_backend.modules.generation_queue.domain.manual_recovery_ports import (
    MaintenanceNotifier,
    ManualRecoveryAudit,
    ManualRecoveryStore,
)
from rag_backend.modules.generation_queue.domain.models import (
    GenerationRun,
    GenerationStatus,
)
from rag_backend.modules.generation_queue.domain.ports import Clock, DriveLock


@dataclass(frozen=True, kw_only=True)
class _Acceptance:
    snapshot: RecoverySnapshot
    stuck: StuckKind
    write: RecoveryWrite


@dataclass(frozen=True, kw_only=True)
class _ExistingRun:
    run: GenerationRun
    lock_version: int | None = None


@dataclass(frozen=True, kw_only=True)
class _CapabilityRun:
    run: GenerationRun | None
    decision: RecoveryDecision | None


_LOCKED_KINDS = frozenset({StuckKind.STALE_RUNNING, StuckKind.ORPHAN})


@dataclass(frozen=True, kw_only=True)
class ManualRecoveryDependencies:
    """The isolated store, audit, lock, notifier, clock and policy."""

    store: ManualRecoveryStore
    audit: ManualRecoveryAudit
    lock: DriveLock
    notifier: MaintenanceNotifier
    clock: Clock
    policy: RecoveryPolicy


class ManualRecoveryService:
    """Recover stuck rows without importing or executing a workflow graph."""

    def __init__(self, deps: ManualRecoveryDependencies) -> None:
        self._deps = deps

    async def reprocess(self, command: ManualReprocessCommand) -> RecoveryResult:
        """Return an existing run or apply exactly one fenced recovery."""
        snapshot = await self._deps.store.load(command)
        if snapshot.missing:
            return await self._not_found()
        if _running(snapshot):
            return await self._reprocess_unlocked(snapshot)
        existing = await self._deps.store.find_existing(snapshot)
        if existing is not None:
            return await self._existing(snapshot, _ExistingRun(run=existing))
        return await self._continue(snapshot, self._classify(snapshot))

    async def _reprocess_unlocked(self, snapshot: RecoverySnapshot) -> RecoveryResult:
        decision = self._classify(snapshot)
        if _refusal_before_existing(decision):
            return await self._refused(snapshot, _required_refusal(decision))
        existing = await self._deps.store.find_existing(snapshot)
        if existing is not None:
            return await self._existing(snapshot, _ExistingRun(run=existing))
        if decision.stuck in _LOCKED_KINDS:
            return await self._take_over(snapshot)
        return await self._reprocess_running(snapshot, decision)

    async def _reprocess_running(
        self, snapshot: RecoverySnapshot, decision: RecoveryDecision
    ) -> RecoveryResult:
        if decision.refusal is not None:
            return await self._refused(snapshot, decision.refusal)
        existing = await self._deps.store.find_existing(snapshot)
        if existing is not None:
            return await self._existing(snapshot, _ExistingRun(run=existing))
        return await self._apply(snapshot, decision)

    async def _continue(
        self, snapshot: RecoverySnapshot, decision: RecoveryDecision
    ) -> RecoveryResult:
        if decision.refusal is not None:
            return await self._refused(snapshot, decision.refusal)
        if decision.stuck in _LOCKED_KINDS:
            return await self._take_over(snapshot)
        return await self._apply(snapshot, decision)

    async def inspect(self, command: ManualReprocessCommand) -> RecoveryCapability:
        """Read workspace capability and progress without writes or notification."""
        snapshot = await self._deps.store.load(command)
        capability = await self._inspect_snapshot(snapshot)
        await self._deps.store.rollback()
        return capability

    async def _inspect_snapshot(self, snapshot: RecoverySnapshot) -> RecoveryCapability:
        if snapshot.missing:
            return await self._capability(
                snapshot,
                _CapabilityRun(
                    run=None, decision=RecoveryDecision(refusal=RefusalCode.UNSUPPORTED)
                ),
            )
        if _running(snapshot):
            return await self._inspect_running(snapshot)
        existing = await self._deps.store.find_existing(snapshot)
        if existing is not None:
            return await self._capability(
                snapshot, _CapabilityRun(run=existing, decision=None)
            )
        return await self._inspect_decision(snapshot, self._classify(snapshot))

    async def _inspect_running(self, snapshot: RecoverySnapshot) -> RecoveryCapability:
        decision = self._classify(snapshot)
        if _refusal_before_existing(decision):
            return await self._capability(
                snapshot, _CapabilityRun(run=snapshot.run, decision=decision)
            )
        existing = await self._deps.store.find_existing(snapshot)
        if existing is not None:
            return await self._capability(
                snapshot, _CapabilityRun(run=existing, decision=None)
            )
        return await self._inspect_decision(snapshot, decision)

    async def _inspect_decision(
        self, snapshot: RecoverySnapshot, decision: RecoveryDecision
    ) -> RecoveryCapability:
        if decision.refusal is not None:
            return await self._capability(
                snapshot, _CapabilityRun(run=snapshot.run, decision=decision)
            )
        if decision.stuck in _LOCKED_KINDS:
            return await self._inspect_locked(snapshot)
        return await self._capability(
            snapshot, _CapabilityRun(run=snapshot.run, decision=decision)
        )

    async def _inspect_locked(self, snapshot: RecoverySnapshot) -> RecoveryCapability:
        try:
            async with self._deps.lock.hold(recovery_lock_keys(snapshot)):
                fresh = await self._deps.store.load(snapshot.command)
                if fresh.missing:
                    return await self._capability(
                        fresh,
                        _CapabilityRun(
                            run=None,
                            decision=RecoveryDecision(refusal=RefusalCode.UNSUPPORTED),
                        ),
                    )
                existing = await self._deps.store.find_existing(fresh)
                if existing is not None:
                    return await self._capability(
                        fresh, _CapabilityRun(run=existing, decision=None)
                    )
                decision = self._classify(fresh)
                return await self._capability(
                    fresh, _CapabilityRun(run=fresh.run, decision=decision)
                )

        except DriveLockBusyError:
            return await self._capability(
                snapshot,
                _CapabilityRun(run=snapshot.run, decision=_BUSY_DECISION),
            )

    async def _take_over(self, snapshot: RecoverySnapshot) -> RecoveryResult:
        try:
            async with self._deps.lock.hold(recovery_lock_keys(snapshot)):
                return await self._fresh_after_lock(snapshot)
        except DriveLockBusyError:
            return await self._refused(snapshot, RefusalCode.DRIVE_ACTIVE)

    async def _fresh_after_lock(self, snapshot: RecoverySnapshot) -> RecoveryResult:
        fresh = await self._deps.store.load(snapshot.command)
        if fresh.missing:
            return await self._not_found()
        if _running(fresh):
            return await self._reprocess_running(fresh, self._classify(fresh))
        existing = await self._deps.store.find_existing(fresh)
        if existing is not None:
            return await self._existing(fresh, _ExistingRun(run=existing))
        return await self._apply(fresh, self._classify(fresh))

    def _classify(self, snapshot: RecoverySnapshot) -> RecoveryDecision:
        return classify_recovery(snapshot, self._deps.clock.now(), self._deps.policy)

    async def _apply(
        self, snapshot: RecoverySnapshot, decision: RecoveryDecision
    ) -> RecoveryResult:
        if decision.stuck is None:
            return await self._refused(snapshot, RefusalCode.UNSUPPORTED)
        mutation = RecoveryMutation(
            snapshot=snapshot,
            stuck=decision.stuck,
            attempt_id=uuid4(),
            requested_at=self._deps.clock.now(),
        )
        write = await self._deps.store.apply(mutation)
        return await self._after_write(
            _Acceptance(snapshot=snapshot, stuck=decision.stuck, write=write)
        )

    async def _after_write(self, acceptance: _Acceptance) -> RecoveryResult:
        snapshot, write = acceptance.snapshot, acceptance.write
        if write.status is WriteStatus.APPLIED and write.run is not None:
            return await self._accepted(acceptance)
        if write.status is WriteStatus.EXISTING and write.run is not None:
            current = _ExistingRun(run=write.run, lock_version=write.lock_version)
            return await self._existing(snapshot, current)
        if write.status is WriteStatus.STALE_VERSION:
            return await self._refused(snapshot, RefusalCode.STALE_VERSION)
        return await self._refused(snapshot, RefusalCode.CONCURRENT_UPDATE)

    async def _accepted(self, acceptance: _Acceptance) -> RecoveryResult:
        snapshot, stuck, write = acceptance.snapshot, acceptance.stuck, acceptance.write
        run = write.run
        if run is None:
            return await self._refused(snapshot, RefusalCode.CONCURRENT_UPDATE)
        project_id = snapshot.command.project_id
        if snapshot.project is not None:
            project_id = snapshot.project.id
        await self._deps.audit.record(
            AuditCommand(
                actor_id=snapshot.command.actor_id,
                project_id=project_id,
                run_id=run.id,
                stuck_kind=stuck,
                lock_version=write.lock_version,
            )
        )
        await self._deps.store.commit()
        notified = await self._notify(run)
        position, eta_seconds = await self._progress(run)
        return RecoveryResult(
            outcome=RecoveryOutcome.QUEUED,
            run=run,
            stuck_kind=stuck,
            lock_version=write.lock_version,
            worker_notified=notified,
            position=position,
            eta_seconds=eta_seconds,
        )

    async def _existing(
        self, snapshot: RecoverySnapshot, current: _ExistingRun
    ) -> RecoveryResult:
        await self._deps.store.commit()
        run = current.run
        notified = await self._notify(run)
        version = current.lock_version or self._lock_version(snapshot)
        position, eta_seconds = await self._progress(run)
        return RecoveryResult(
            outcome=RecoveryOutcome.EXISTING,
            run=run,
            stuck_kind=manual_stuck_kind(run),
            lock_version=version,
            worker_notified=notified,
            position=position,
            eta_seconds=eta_seconds,
        )

    async def _notify(self, run: GenerationRun) -> bool:
        try:
            return await self._deps.notifier.notify(MaintenanceNotice(run_id=run.id))
        except Exception:
            return False

    async def _refused(
        self, snapshot: RecoverySnapshot, refusal: RefusalCode
    ) -> RecoveryResult:
        await self._deps.store.rollback()
        return RecoveryResult(
            outcome=RecoveryOutcome.REFUSED,
            refusal=refusal,
            lock_version=self._lock_version(snapshot),
        )

    async def _not_found(self) -> RecoveryResult:
        await self._deps.store.rollback()
        return RecoveryResult(outcome=RecoveryOutcome.NOT_FOUND)

    async def _progress(self, run: GenerationRun) -> tuple[int | None, int | None]:
        placed = await self._deps.store.position(run)
        if placed is None:
            return None, None
        elapsed = max(0, int((placed.eta - self._deps.clock.now()).total_seconds()))
        return placed.position, elapsed

    async def _capability(
        self, snapshot: RecoverySnapshot, current: _CapabilityRun
    ) -> RecoveryCapability:
        run, decision = current.run, current.decision
        position, eta_seconds = (
            await self._progress(run) if run is not None else (None, None)
        )
        if run is not None and decision is None:
            return RecoveryCapability(
                can_reprocess=True,
                run=run,
                lock_version=self._lock_version(snapshot),
                stuck_kind=manual_stuck_kind(run),
                position=position,
                eta_seconds=eta_seconds,
            )
        return RecoveryCapability(
            can_reprocess=decision is not None and decision.stuck is not None,
            run=run,
            lock_version=self._lock_version(snapshot),
            stuck_kind=decision.stuck if decision is not None else None,
            refusal=(
                decision.refusal if decision is not None else RefusalCode.UNSUPPORTED
            ),
            position=position,
            eta_seconds=eta_seconds,
        )

    @staticmethod
    def _lock_version(snapshot: RecoverySnapshot) -> int | None:
        return snapshot.project.lock_version if snapshot.project is not None else None


def _running(snapshot: RecoverySnapshot) -> bool:
    run = snapshot.run
    return run is not None and run.status is GenerationStatus.RUNNING


def _refusal_before_existing(decision: RecoveryDecision) -> bool:
    return (
        decision.refusal is not None
        and decision.refusal is not RefusalCode.STALE_VERSION
    )


def _required_refusal(decision: RecoveryDecision) -> RefusalCode:
    return decision.refusal if decision.refusal is not None else RefusalCode.UNSUPPORTED


_BUSY_DECISION = RecoveryDecision(refusal=RefusalCode.DRIVE_ACTIVE)


__all__ = ["ManualRecoveryDependencies", "ManualRecoveryService"]
