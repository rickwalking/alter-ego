"""A generation run whose workflow failed is not marked succeeded.

Feature: phase_failure_cause_ae0600.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from rag_backend.modules.generation_queue.application.generation_events import (
    current_workflow_failure,
    generation_event_run,
    generation_event_scope,
    note_workflow_failure,
)
from rag_backend.modules.generation_queue.application.job_handler import (
    GenerationJobHandler,
    HandlerDependencies,
    Verdict,
    VerdictKind,
)
from rag_backend.modules.generation_queue.constants import (
    ERROR_WORKFLOW_FAILED,
    EVENT_RUN_DEAD_LETTER,
    EVENT_RUN_SUCCEEDED,
    OUTCOME_FAILED,
    OUTCOME_SUCCEEDED,
)
from rag_backend.modules.generation_queue.domain.generation_events import (
    GenerationEventInput,
    GenerationEventRun,
)
from rag_backend.modules.generation_queue.domain.models import (
    AttemptDeadLetterCommand,
    GenerationKind,
    GenerationRun,
    GenerationStatus,
)
from rag_backend.modules.generation_queue.domain.ports import StepOutcome, StepTracker
from rag_backend.modules.generation_queue.events_public import (
    WorkflowOutcomeObservation,
    record_workflow_outcome,
)
from tests.unit.modules.generation_queue.queue_fakes import (
    FakeLock,
    FakeNotices,
    FakeStore,
    FixedClock,
    make_run,
    resume_run,
)

_PROJECT = "p-ae0600"
_CAUSE = "ValueError: en_translation_parse_failed"
_PHASE = "outline"


@dataclass
class _Recorder:
    events: list[GenerationEventInput] = field(default_factory=list)

    async def record(
        self, run: GenerationEventRun, event: GenerationEventInput
    ) -> bool:
        del run
        self.events.append(event)
        return True


@dataclass
class _Completion:
    calls: list[tuple[str, bool]] = field(default_factory=list)

    async def completed(self, project_id: str, *, succeeded: bool = True) -> None:
        self.calls.append((project_id, succeeded))


@dataclass
class _OutcomeExecutor:
    """Runs one phase and records the scripted workflow outcomes, then DONE."""

    outcomes: tuple[str, ...]

    async def lock_keys(self, run: GenerationRun) -> list[str]:
        return [f"run:{run.id}"]

    async def execute(self, run: GenerationRun, tracker: StepTracker) -> StepOutcome:
        del run
        await tracker.begin(_PHASE)
        for outcome in self.outcomes:
            await record_workflow_outcome(
                WorkflowOutcomeObservation(
                    project_id=_PROJECT, phase=_PHASE, outcome=outcome
                )
            )
            if outcome == OUTCOME_FAILED:
                note_workflow_failure(_CAUSE)
        await tracker.finish(_PHASE)
        return StepOutcome.DONE


@dataclass
class _Harness:
    store: FakeStore
    notices: FakeNotices
    recorder: _Recorder
    completion: _Completion
    run: GenerationRun


def _harness() -> _Harness:
    store = FakeStore()
    run = store.add(resume_run(carousel_project_id=_PROJECT))
    return _Harness(store, FakeNotices(), _Recorder(), _Completion(), run)


async def _handle(harness: _Harness, executor: _OutcomeExecutor) -> Verdict:
    handler = GenerationJobHandler(
        HandlerDependencies(
            store=harness.store,
            lock=FakeLock(),
            executors={GenerationKind.WORKFLOW_RESUME: executor},
            notices=harness.notices,
            clock=FixedClock(),
            is_provider_error=lambda _exc: False,
            uniform=lambda low, _high: low,
            events=harness.recorder,
            completion=harness.completion,
        )
    )
    return await handler.handle(harness.run.id)


def _event_types(harness: _Harness) -> list[str]:
    return [event.event_type for event in harness.recorder.events]


@pytest.mark.unit
@pytest.mark.asyncio
class TestFailedWorkflowRunStatus:
    async def test_failed_workflow_dead_letters_the_run_with_its_cause(self) -> None:
        # Scenario: A generation run whose workflow failed is not marked succeeded
        harness = _harness()

        verdict = await _handle(harness, _OutcomeExecutor((OUTCOME_FAILED,)))

        assert verdict == Verdict(VerdictKind.DONE)
        stored = harness.store.runs[harness.run.id]
        assert stored.status is GenerationStatus.DEAD_LETTER
        assert stored.last_error_code == ERROR_WORKFLOW_FAILED
        assert len(harness.store.dead) == 1
        command = harness.store.dead[0]
        assert isinstance(command, AttemptDeadLetterCommand)
        assert command.error_code == ERROR_WORKFLOW_FAILED
        assert command.error == _CAUSE
        assert EVENT_RUN_DEAD_LETTER in _event_types(harness)
        assert EVENT_RUN_SUCCEEDED not in _event_types(harness)
        assert harness.notices.staged == []
        assert harness.completion.calls == [(_PROJECT, False)]

    async def test_dead_letter_event_names_the_workflow_failure(self) -> None:
        # Scenario: A generation run whose workflow failed is not marked succeeded
        harness = _harness()

        await _handle(harness, _OutcomeExecutor((OUTCOME_FAILED,)))

        dead = [
            event
            for event in harness.recorder.events
            if event.event_type == EVENT_RUN_DEAD_LETTER
        ]
        assert len(dead) == 1
        assert dead[0].error_code == ERROR_WORKFLOW_FAILED
        assert dead[0].outcome == "dead_letter"

    async def test_later_success_in_the_same_drive_still_succeeds(self) -> None:
        # Scenario: A later successful outcome in the same drive still succeeds
        harness = _harness()

        await _handle(harness, _OutcomeExecutor((OUTCOME_FAILED, OUTCOME_SUCCEEDED)))

        stored = harness.store.runs[harness.run.id]
        assert stored.status is GenerationStatus.SUCCEEDED
        assert harness.store.dead == []
        assert harness.completion.calls == [(_PROJECT, True)]

    async def test_no_failure_note_keeps_the_run_succeeded(self) -> None:
        # Scenario: A resume that only got stuck does not dead-letter the run
        harness = _harness()

        await _handle(harness, _OutcomeExecutor(()))

        assert harness.store.runs[harness.run.id].status is GenerationStatus.SUCCEEDED
        assert EVENT_RUN_SUCCEEDED in _event_types(harness)


@pytest.mark.unit
class TestWorkflowFailureNote:
    def test_note_outside_a_run_scope_is_a_no_op(self) -> None:
        note_workflow_failure(_CAUSE)

        assert current_workflow_failure() is None

    @pytest.mark.asyncio
    async def test_note_is_scoped_to_the_run(self) -> None:
        run = generation_event_run(make_run(carousel_project_id=_PROJECT))

        async with generation_event_scope(run, _Recorder()):
            assert current_workflow_failure() is None
            note_workflow_failure(_CAUSE)
            assert current_workflow_failure() == _CAUSE
            note_workflow_failure(None)
            assert current_workflow_failure() is None
        assert current_workflow_failure() is None
