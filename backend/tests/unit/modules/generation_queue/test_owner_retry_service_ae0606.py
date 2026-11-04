"""The owner Retry service: one write, one audit, nothing on a refusal.

Feature: tests/features/carousel_owner_retry_ae0606.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pytest
from structlog.testing import capture_logs

from rag_backend.modules.generation_queue.application.owner_retry import (
    OwnerRetryDependencies,
    OwnerRetryService,
)
from rag_backend.modules.generation_queue.application.owner_retry_feedback import (
    retry_feedback,
)
from rag_backend.modules.generation_queue.domain.owner_retry import (
    CarouselRetryState,
    CheckpointFacts,
    OwnerRetryCommand,
    QueueFacts,
    RetryFacts,
    RetryKind,
    RetryRefusal,
    RetrySurface,
)
from rag_backend.modules.generation_queue.domain.owner_retry_ports import (
    RetryAuditCommand,
    RetryPlan,
    RetryRefusedError,
    RetryWrite,
)

_OWNER = "owner-1"
_COMMAND = OwnerRetryCommand(
    project_id="p-1", actor_id=_OWNER, surface=RetrySurface.WEB, expected_version=4
)
_FACTS = RetryFacts(
    actor_id=_OWNER,
    carousel=CarouselRetryState(
        owner_id=_OWNER,
        assigned_reviewer_id=None,
        topic="Topic",
        phase="content",
        phase_status="awaiting_human",
        status="pending",
        workflow_status="draft",
        lock_version=4,
    ),
    checkpoint=CheckpointFacts(
        present=True, blocker="persona_score_too_low", persona_score=61.6
    ),
    queue=QueueFacts(),
)
_WRITTEN = RetryWrite(lock_version=5, phase="content", phase_status="in_progress")


@dataclass
class _Store:
    facts: RetryFacts | None = _FACTS
    write: RetryWrite = _WRITTEN
    plans: list[RetryPlan] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    commits: int = 0
    rollbacks: int = 0
    lost_lock: bool = False
    commit_error: Exception | None = None
    announce_error: Exception | None = None

    async def read(self, command: OwnerRetryCommand) -> RetryFacts | None:
        del command
        if self.lost_lock:
            raise RetryRefusedError(RetryRefusal.CONCURRENT_UPDATE)
        return self.facts

    async def announce(self, project_id: str, phase: str) -> None:
        if self.announce_error is not None:
            raise self.announce_error
        self.events.append(f"announce:{project_id}:{phase}")

    async def apply(self, plan: RetryPlan) -> RetryWrite:
        self.plans.append(plan)
        return self.write

    async def commit(self) -> None:
        if self.commit_error is not None:
            raise self.commit_error
        self.commits += 1
        self.events.append("commit")

    async def rollback(self) -> None:
        self.rollbacks += 1


@dataclass
class _Audit:
    records: list[RetryAuditCommand] = field(default_factory=list)
    error: Exception | None = None

    async def record(self, command: RetryAuditCommand) -> None:
        if self.error is not None:
            raise self.error
        self.records.append(command)


def _service(
    store: _Store, audit: _Audit, *, owns_transaction: bool = True
) -> OwnerRetryService:
    return OwnerRetryService(
        OwnerRetryDependencies(store=store, audit=audit),
        owns_transaction=owns_transaction,
    )


@pytest.mark.unit
class TestOwnerRetryService:
    # Scenario: A blocked content gate is revised with the system retry feedback line
    async def test_an_accepted_revise_sends_and_audits_the_feedback_line(self) -> None:
        store, audit = _Store(), _Audit()

        result = await _service(store, audit).retry(_COMMAND)

        assert result.accepted is True
        assert result.kind is RetryKind.REVISE
        assert result.lock_version == 5
        assert result.phase_status == "in_progress"
        plan = store.plans[0]
        assert "persona_score_too_low" in plan.feedback
        assert "persona score 62, threshold 70" in plan.feedback
        assert plan.feedback.strip() == plan.feedback
        assert audit.records == [RetryAuditCommand(plan=plan, write=_WRITTEN)]
        assert (store.commits, store.rollbacks) == (1, 0)
        assert store.events == ["commit", "announce:p-1:content"]

    # Scenario: A failed phase parked before its node is re-driven
    async def test_a_redrive_sends_no_feedback_line(self) -> None:
        facts = replace(
            _FACTS,
            carousel=replace(_FACTS.carousel, phase_status="failed"),
            checkpoint=CheckpointFacts(present=True, parked=True),
        )
        store, audit = _Store(facts=facts), _Audit()

        result = await _service(store, audit).retry(_COMMAND)

        assert result.kind is RetryKind.REDRIVE
        assert store.plans[0].feedback == ""
        assert len(audit.records) == 1

    # Scenario: A tap from someone who does not own the carousel changes nothing
    async def test_a_refused_decision_writes_nothing(self) -> None:
        store, audit = _Store(facts=replace(_FACTS, actor_id="stranger")), _Audit()

        result = await _service(store, audit).retry(_COMMAND)

        assert result.accepted is False
        assert result.refusal is RetryRefusal.NOT_OWNER
        assert store.plans == []
        assert audit.records == []
        assert (store.commits, store.rollbacks) == (0, 1)

    async def test_a_missing_carousel_is_not_found(self) -> None:
        store, audit = _Store(facts=None), _Audit()

        result = await _service(store, audit).retry(_COMMAND)

        assert result.refusal is RetryRefusal.NOT_FOUND
        assert store.rollbacks == 1

    # Scenario: A lost autopilot run compare-and-set rolls back the stage and the audit
    async def test_a_lost_write_is_refused_without_an_audit(self) -> None:
        lost = RetryWrite(refusal=RetryRefusal.CONCURRENT_UPDATE)
        store, audit = _Store(write=lost), _Audit()

        result = await _service(store, audit).retry(_COMMAND)

        assert result.refusal is RetryRefusal.CONCURRENT_UPDATE
        assert audit.records == []
        assert (store.commits, store.rollbacks) == (0, 1)

    async def test_telegram_leaves_the_transaction_to_the_webhook(self) -> None:
        store, audit = _Store(), _Audit()
        service = _service(store, audit, owns_transaction=False)

        accepted = await service.retry(_COMMAND)
        store.facts = replace(_FACTS, actor_id="stranger")
        refused = await service.retry(_COMMAND)

        assert accepted.accepted is True
        assert refused.accepted is False
        assert (store.commits, store.rollbacks) == (0, 0)
        assert store.events == []
        await service.announce(accepted, "p-1")
        await service.announce(refused, "p-1")
        assert store.events == ["announce:p-1:content"]

    # Scenario: A lost autopilot run compare-and-set rolls back the stage and the audit
    async def test_a_failed_audit_announces_nothing_and_raises(self) -> None:
        store, audit = _Store(), _Audit(error=RuntimeError("audit down"))

        with pytest.raises(RuntimeError, match="audit down"):
            await _service(store, audit).retry(_COMMAND)

        assert store.events == []
        assert store.commits == 0

    async def test_a_failed_commit_announces_nothing_and_raises(self) -> None:
        store = _Store(commit_error=RuntimeError("commit lost"))

        with pytest.raises(RuntimeError, match="commit lost"):
            await _service(store, _Audit()).retry(_COMMAND)

        assert store.events == []

    async def test_a_failed_announce_is_logged_and_the_retry_stands(self) -> None:
        store = _Store(announce_error=OSError("bus down"))

        with capture_logs() as logs:
            result = await _service(store, _Audit()).retry(_COMMAND)
            await _service(store, _Audit(), owns_transaction=False).announce(
                result, "p-1"
            )

        assert result.accepted is True
        assert store.events == ["commit"]
        failed = [e for e in logs if e["event"] == "carousel_retry_announce_failed"]
        assert [(e["project_id"], e["error"]) for e in failed] == [
            ("p-1", "OSError"),
            ("p-1", "OSError"),
        ]

    # Scenario: A lost lock is refused as concurrent_update
    async def test_a_lost_lock_on_read_is_refused(self) -> None:
        store, audit = _Store(lost_lock=True), _Audit()

        result = await _service(store, audit).retry(_COMMAND)
        capability = await _service(store, audit).inspect(_COMMAND)

        assert result.refusal is RetryRefusal.CONCURRENT_UPDATE
        assert capability.refusal is RetryRefusal.CONCURRENT_UPDATE
        assert capability.can_retry is False
        assert store.plans == []
        assert store.rollbacks == 2

    async def test_a_reopen_announces_no_run(self) -> None:
        facts = replace(
            _FACTS,
            carousel=replace(
                _FACTS.carousel, phase="final_review", phase_status="rejected"
            ),
        )
        store = _Store(facts=facts)

        result = await _service(store, _Audit()).retry(_COMMAND)

        assert result.kind is RetryKind.REOPEN
        assert store.events == ["commit"]

    # Scenario: The retry capability is read without any change
    async def test_inspect_reads_the_capability_and_writes_nothing(self) -> None:
        store, audit = _Store(), _Audit()

        capability = await _service(store, audit).inspect(_COMMAND)

        assert capability.can_retry is True
        assert capability.kind is RetryKind.REVISE
        assert capability.refusal is None
        assert capability.lock_version == 4
        assert store.plans == []
        assert audit.records == []
        assert store.rollbacks == 1

    async def test_inspect_reports_a_refusal(self) -> None:
        store = _Store(facts=replace(_FACTS, queue=QueueFacts(active_run=True)))

        capability = await _service(store, _Audit()).inspect(_COMMAND)

        assert capability.can_retry is False
        assert capability.refusal is RetryRefusal.RUN_IN_PROGRESS

    async def test_inspect_of_a_missing_carousel(self) -> None:
        capability = await _service(_Store(facts=None), _Audit()).inspect(_COMMAND)

        assert capability.can_retry is False
        assert capability.refusal is RetryRefusal.NOT_FOUND


@pytest.mark.unit
class TestRetryFeedback:
    def test_the_line_names_the_phase_and_the_reason(self) -> None:
        facts = replace(_FACTS, checkpoint=CheckpointFacts(present=True))

        line = retry_feedback(facts, "carousel_rejected")

        assert "content phase" in line
        assert "Reason: carousel_rejected." in line
        assert "Measured" not in line

    def test_a_score_at_the_floor_is_not_reported(self) -> None:
        facts = replace(
            _FACTS, checkpoint=CheckpointFacts(present=True, persona_score=70.0)
        )

        assert "Measured" not in retry_feedback(facts, "gate_blocked")

    def test_a_score_below_the_floor_is_reported(self) -> None:
        line = retry_feedback(_FACTS, "gate_blocked")

        assert "Measured: persona score 62, threshold 70." in line
