"""In-process autopilot runner against a fake editorial driver (AE-0354).

Gherkin: tests/features/autopilot_runner.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import UUID, uuid4

import pytest

from rag_backend.domain.constants.carousel import CAROUSEL_HEIGHT, CAROUSEL_WIDTH
from rag_backend.modules.autopilot.application.feedback import (
    ReviseFeedbackRequest,
    revise_feedback,
)
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.constants import (
    EVENT_TYPE_READY_FOR_OWNER,
    GATE_CONTENT,
    GATE_DESIGN,
    GATE_FINAL_REVIEW,
    GATE_IMAGES,
    GATE_OUTLINE,
    GATE_RESEARCH,
    PHASE_STATUS_AWAITING,
    REASON_OWNER_UNCONFIGURED,
    REASON_PERSONA_SCORE,
    REASON_PROJECT_MISSING,
    REASON_REVISION_CAP,
    REASON_START_FAILED,
    REASON_TOPIC_MISSING,
)
from rag_backend.modules.autopilot.domain.gate import (
    AttachProjectCommand,
    GateSnapshot,
    ImageFact,
    OwnerReadyNotice,
    ProjectSpec,
    ResearchSourceFact,
    ResumeCommand,
    ResumeResult,
    ResumeStatus,
    StartAttemptCommand,
    StartCommand,
    StartStatus,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.recovery import EscalationMark, ReworkIntent
from rag_backend.modules.autopilot.notify_constants import (
    REASON_NOTIFIER_UNCONFIGURED,
)
from rag_backend.modules.editorial.public import (
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
)

_PROJECT = "11111111-1111-1111-1111-111111111111"
_OWNER = "owner-1"
_NEXT = {
    GATE_RESEARCH: GATE_OUTLINE,
    GATE_OUTLINE: GATE_CONTENT,
    GATE_CONTENT: GATE_DESIGN,
    GATE_DESIGN: GATE_IMAGES,
    GATE_IMAGES: GATE_FINAL_REVIEW,
}
_IDLE_CAP = 20


def _topic(candidate_id: UUID) -> TopicCandidate:
    return TopicCandidate(
        candidate_id=candidate_id,
        title="Agents that ship",
        angle="operator",
        why_viral="three launches",
        audience="builders",
        niche="ai",
        brief="A short brief.",
        sources=("https://example.com/story",),
        score=80,
        signal_hash="abc",
        status="accepted",
    )


def _run(state: AutopilotRunState, project_id: str | None = None) -> AutopilotRun:
    return AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id=project_id,
        state=state,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )


def _snapshot(phase: str, score: float | None, revisions: int) -> GateSnapshot:
    source = ResearchSourceFact(content="body", summary="", key_points=())
    image = ImageFact(
        present=True,
        is_jpeg=True,
        width=CAROUSEL_WIDTH,
        height=CAROUSEL_HEIGHT,
    )
    return GateSnapshot(
        phase=phase,
        phase_status=PHASE_STATUS_AWAITING,
        lock_version=4,
        sources=(source, source, source),
        outline_count=6,
        slides_total=6,
        persona_score=score,
        forbidden_hits=(),
        presentation_blockers=(),
        images=tuple(image for _ in range(6)),
        revisions_used=revisions,
        stale=False,
    )


@dataclass
class _Runs:
    run: AutopilotRun
    topic: TopicCandidate | None
    accept: bool = True
    accept_attach: bool = True

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        if self.run.state is query.state:
            return [self.run]
        return []

    async def get_topic(self, candidate_id: UUID) -> TopicCandidate | None:
        return self.topic

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        return self.run if self.run.run_id == run_id else None

    async def attach_project(self, command: AttachProjectCommand) -> bool:
        if not self.accept_attach:
            return False
        self.run = replace(self.run, carousel_project_id=command.project_id)
        return True

    async def note_start_attempt(self, command: StartAttemptCommand) -> bool:
        self.run = replace(
            self.run,
            start_attempts=command.attempts,
            state_reason=command.reason,
        )
        return True

    async def transition(self, command: TransitionCommand) -> bool:
        if not self.accept or self.run.state is not command.expected:
            return False
        self.run = replace(self.run, state=command.new, state_reason=command.reason)
        return True


@dataclass
class _Editorial:
    phase: str = GATE_RESEARCH
    score: float | None = 90.0
    revisions: int = 0
    start_status: StartStatus = StartStatus.STARTED
    conflict_once: bool = False
    resume_status: ResumeStatus = ResumeStatus.APPLIED
    starts: int = 0
    resumes: list[ResumeCommand] | None = None
    _conflicted: bool = False

    def __post_init__(self) -> None:
        if self.resumes is None:
            self.resumes = []

    async def create_project(self, spec: ProjectSpec) -> str:
        assert spec.owner_user_id == _OWNER
        return _PROJECT

    async def start(self, command: StartCommand) -> StartStatus:
        self.starts += 1
        return self.start_status

    async def read_gate(self, project_id: str) -> GateSnapshot:
        return _snapshot(self.phase, self.score, self.revisions)

    async def resume(self, command: ResumeCommand) -> ResumeResult:
        assert self.resumes is not None
        self.resumes.append(command)
        if self.conflict_once and not self._conflicted:
            self._conflicted = True
            return ResumeResult(status=ResumeStatus.VERSION_CONFLICT)
        if self.resume_status is not ResumeStatus.APPLIED:
            return ResumeResult(status=self.resume_status)
        if command.action == REVIEW_ACTION_REVISE:
            self.revisions += 1
            return ResumeResult(status=ResumeStatus.APPLIED)
        if command.action == REVIEW_ACTION_APPROVE:
            self.phase = _NEXT[self.phase]
        return ResumeResult(status=ResumeStatus.APPLIED)


@dataclass
class _Recovery:
    """In-memory ``RunRecoveryStore`` bound to the fake run (QA r1)."""

    runs: _Runs | None = None
    rollbacks: int = 0
    marks: list[EscalationMark] = field(default_factory=list)
    cleared: int = 0

    async def queue_rework(self, intent: ReworkIntent) -> bool:
        assert self.runs is not None
        self.runs.run = replace(
            self.runs.run, rework_phase=intent.phase, rework_feedback=intent.feedback
        )
        return True

    async def clear_rework(self, run_id: UUID) -> None:
        self.cleared += 1
        if self.runs is not None:
            self.runs.run = replace(
                self.runs.run, rework_phase=None, rework_feedback=None
            )

    async def mark_escalated(self, mark: EscalationMark) -> None:
        self.marks.append(mark)
        if self.runs is not None:
            self.runs.run = replace(self.runs.run, escalated_version=mark.version)

    async def rollback(self) -> None:
        self.rollbacks += 1


class _Notices:
    def __init__(self) -> None:
        self.events: list[OwnerReadyNotice] = []

    async def notify_ready(self, notice: OwnerReadyNotice) -> None:
        self.events.append(notice)


def _runner(
    runs: _Runs,
    editorial: _Editorial,
    notices: _Notices,
    owner: str = _OWNER,
    notifier_configured: bool = True,
) -> AutopilotRunner:
    return AutopilotRunner(
        RunnerDependencies(
            runs=runs,
            topics=runs,
            editorial=editorial,
            notices=notices,
            recovery=_Recovery(runs=runs),
            owner_user_id=owner,
            notifier_configured=notifier_configured,
        )
    )


async def _until_idle(runner: AutopilotRunner) -> int:
    for steps in range(_IDLE_CAP):
        if await runner.tick() == 0:
            return steps
    raise AssertionError("runner did not go idle")


@pytest.mark.asyncio
async def test_clean_run_stops_at_final_review_and_emits_once() -> None:
    """Scenario: Clean run reaches the owner."""
    run = _run(AutopilotRunState.QUEUED)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    editorial = _Editorial()
    notices = _Notices()
    steps = await _until_idle(_runner(runs, editorial, notices))

    assert steps == 7
    assert runs.run.state is AutopilotRunState.AWAITING_OWNER
    assert editorial.resumes is not None
    approved_final = [
        command
        for command in editorial.resumes
        if command.phase == GATE_FINAL_REVIEW
        and command.action == REVIEW_ACTION_APPROVE
    ]
    assert approved_final == []
    assert len(notices.events) == 1
    assert notices.events[0].project_id == _PROJECT
    assert notices.events[0].revision == 4
    assert notices.events[0].persona_score == 90.0
    assert notices.events[0].sources_count == 3
    assert EVENT_TYPE_READY_FOR_OWNER == "content.autopilot.ready_for_owner"


@pytest.mark.asyncio
async def test_missing_bot_token_escalates_instead_of_notifying() -> None:
    """Scenario: Missing bot token escalates and does not call Telegram."""
    run = _run(AutopilotRunState.GENERATING, project_id=_PROJECT)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    editorial = _Editorial(phase=GATE_FINAL_REVIEW)
    notices = _Notices()
    await _until_idle(_runner(runs, editorial, notices, notifier_configured=False))

    assert runs.run.state is AutopilotRunState.ESCALATED
    assert runs.run.state_reason == REASON_NOTIFIER_UNCONFIGURED
    assert notices.events == []


@pytest.mark.asyncio
async def test_low_persona_score_revises_twice_then_escalates() -> None:
    """Scenario: Low persona score is revised then escalated."""
    run = _run(AutopilotRunState.QUEUED)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    editorial = _Editorial(phase=GATE_CONTENT, score=62.0)
    notices = _Notices()
    await _until_idle(_runner(runs, editorial, notices))

    assert editorial.resumes is not None
    revises = [
        command
        for command in editorial.resumes
        if command.action == REVIEW_ACTION_REVISE
    ]
    assert len(revises) == 2
    assert all(REASON_PERSONA_SCORE in command.feedback for command in revises)
    assert runs.run.state is AutopilotRunState.ESCALATED
    assert runs.run.state_reason == REASON_PERSONA_SCORE
    assert notices.events == []


@pytest.mark.asyncio
async def test_version_conflict_applies_exactly_one_approve() -> None:
    """Scenario: Version conflict is retried safely."""
    run = _run(AutopilotRunState.GENERATING, _PROJECT)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    editorial = _Editorial(conflict_once=True)
    notices = _Notices()
    runner = _runner(runs, editorial, notices)

    assert await runner.tick() == 1
    assert await runner.tick() == 1

    assert editorial.resumes is not None
    assert len(editorial.resumes) == 2
    assert editorial.phase == GATE_OUTLINE
    assert runs.run.state is AutopilotRunState.GENERATING


@pytest.mark.asyncio
async def test_provider_outage_fails_the_run_on_the_third_start() -> None:
    """Scenario: Provider outage on start."""
    run = _run(AutopilotRunState.QUEUED)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    editorial = _Editorial(start_status=StartStatus.PROVIDER_OUTAGE)
    runner = _runner(runs, editorial, _Notices())

    assert await runner.tick() == 1
    assert runs.run.state is AutopilotRunState.QUEUED
    assert runs.run.start_attempts == 1
    assert await runner.tick() == 1
    assert runs.run.start_attempts == 2
    assert await runner.tick() == 1
    assert runs.run.state is AutopilotRunState.FAILED
    assert runs.run.state_reason == REASON_START_FAILED
    assert editorial.starts == 3


@pytest.mark.asyncio
async def test_failed_cas_does_not_emit_ready() -> None:
    run = _run(AutopilotRunState.GENERATING, _PROJECT)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    editorial = _Editorial(phase=GATE_FINAL_REVIEW)
    runs.accept = False
    notices = _Notices()
    await _runner(runs, editorial, notices).tick()
    assert notices.events == []


@pytest.mark.asyncio
async def test_missing_owner_or_topic_or_project_fails_the_run() -> None:
    queued = _run(AutopilotRunState.QUEUED)
    runs = _Runs(run=queued, topic=_topic(queued.topic_candidate_id))
    editorial = _Editorial()
    await _runner(runs, editorial, _Notices(), owner="  ").tick()
    assert runs.run.state is AutopilotRunState.FAILED
    assert runs.run.state_reason == REASON_OWNER_UNCONFIGURED
    assert editorial.starts == 0

    queued = _run(AutopilotRunState.QUEUED)
    runs = _Runs(run=queued, topic=None)
    await _runner(runs, editorial, _Notices()).tick()
    assert runs.run.state_reason == REASON_TOPIC_MISSING

    active = _run(AutopilotRunState.GENERATING, None)
    runs = _Runs(run=active, topic=_topic(active.topic_candidate_id))
    await _runner(runs, editorial, _Notices()).tick()
    assert runs.run.state_reason == REASON_PROJECT_MISSING


@pytest.mark.asyncio
async def test_revision_cap_escalates_after_one_resume() -> None:
    run = _run(AutopilotRunState.GENERATING, _PROJECT)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    editorial = _Editorial(resume_status=ResumeStatus.REVISION_CAP)
    await _runner(runs, editorial, _Notices()).tick()
    assert editorial.resumes is not None
    assert len(editorial.resumes) == 1
    assert runs.run.state is AutopilotRunState.ESCALATED
    assert runs.run.state_reason == REASON_REVISION_CAP


@pytest.mark.asyncio
async def test_resume_outage_is_one_call_per_tick() -> None:
    run = _run(AutopilotRunState.GENERATING, _PROJECT)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
    editorial = _Editorial(resume_status=ResumeStatus.PROVIDER_OUTAGE)
    runner = _runner(runs, editorial, _Notices())
    assert await runner.tick() == 1
    assert await runner.tick() == 1
    assert editorial.resumes is not None
    assert len(editorial.resumes) == 2
    assert runs.run.state is AutopilotRunState.GENERATING


@pytest.mark.asyncio
async def test_attach_miss_leaves_the_run_queued() -> None:
    run = _run(AutopilotRunState.QUEUED)
    runs = _Runs(run=run, topic=_topic(run.topic_candidate_id), accept_attach=False)
    editorial = _Editorial()
    assert await _runner(runs, editorial, _Notices()).tick() == 0
    assert runs.run.state is AutopilotRunState.QUEUED
    assert editorial.starts == 0


def test_revise_feedback_renders_the_prompt() -> None:
    text = revise_feedback(
        ReviseFeedbackRequest(
            phase=GATE_CONTENT, reason=REASON_PERSONA_SCORE, detail="62.0"
        )
    )
    assert GATE_CONTENT in text
    assert REASON_PERSONA_SCORE in text
    assert "62.0" in text
