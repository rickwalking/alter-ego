"""Attempt budgets, retry delays, failure classes and stored payloads."""

from __future__ import annotations

from datetime import timedelta

import pytest

from rag_backend.modules.generation_queue.constants import (
    ERROR_PHASE_BUDGET,
    ERROR_RUN_BUDGET,
)
from rag_backend.modules.generation_queue.domain import budget
from rag_backend.modules.generation_queue.domain.errors import (
    BudgetExhaustedError,
    FailureClass,
    PermanentGenerationError,
    classify,
)
from rag_backend.modules.generation_queue.domain.models import (
    AutopilotDrivePayload,
    GenerationStatus,
    WorkflowResumePayload,
    autopilot_stage,
    is_active,
    resume_stage,
)

_EMPTY = budget.AttemptCounts(attempts=0, phase_attempts={})
_BUDGET = budget.AttemptBudget()


def _never_provider(_exc: BaseException) -> bool:
    return False


def test_fourth_start_of_a_phase_exceeds_its_budget() -> None:
    """Scenario: A phase that keeps failing is parked once its budget is spent"""
    counts = _EMPTY
    for _ in range(3):
        counts = budget.begin(counts, "content")
        assert budget.exhausted(counts, "content", _BUDGET) is None
    counts = budget.begin(counts, "content")
    assert budget.exhausted(counts, "content", _BUDGET) == ERROR_PHASE_BUDGET
    assert counts.attempts == 4


def test_run_budget_counts_unfinished_starts_across_phases() -> None:
    """Scenario: A phase that keeps failing is parked once its budget is spent"""
    counts = budget.AttemptCounts(attempts=10, phase_attempts={})
    counts = budget.begin(counts, "design")
    assert budget.exhausted(counts, "design", _BUDGET) == ERROR_RUN_BUDGET


def test_a_run_that_keeps_advancing_is_never_poison() -> None:
    """Scenario: A run that keeps advancing is never taken for poison"""
    counts = _EMPTY
    for index in range(50):
        phase = f"phase-{index}"
        counts = budget.begin(counts, phase)
        assert budget.exhausted(counts, phase, _BUDGET) is None
        counts = budget.finish(counts, phase)
    assert counts == _EMPTY


def test_finish_takes_back_one_start_and_clears_the_phase() -> None:
    """Scenario: A run that keeps advancing is never taken for poison"""
    counts = budget.begin(budget.begin(_EMPTY, "images"), "images")
    finished = budget.finish(counts, "images")
    assert finished.attempts == 1
    assert finished.phase_attempts == {}
    assert budget.finish(finished, "images") == finished


def test_reset_phase_forgets_only_that_phase() -> None:
    """Scenario: A dead-lettered run is requeued once"""
    counts = budget.AttemptCounts(attempts=6, phase_attempts={"a": 4, "b": 1})
    reset = budget.reset_phase(counts, "a")
    assert reset == budget.AttemptCounts(attempts=2, phase_attempts={"b": 1})
    assert budget.reset_phase(counts, None) == counts
    assert budget.reset_phase(budget.AttemptCounts(1, {}), "x").attempts == 1


@pytest.mark.parametrize(
    ("attempt", "low", "high"),
    [(0, 24, 36), (1, 24, 36), (2, 48, 72), (3, 96, 144), (20, 1440, 2160)],
)
def test_retry_delay_doubles_from_30s_to_30min_with_jitter(
    attempt: int, low: float, high: float
) -> None:
    """Scenario: A transient failure retries with backoff and jitter"""
    lowest = budget.retry_delay(attempt, lambda a, _b: a)
    highest = budget.retry_delay(attempt, lambda _a, b: b)
    assert lowest == timedelta(seconds=low)
    assert highest == timedelta(seconds=high)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError(), FailureClass.TRANSIENT),
        (ConnectionResetError(), FailureClass.TRANSIENT),
        (RuntimeError("unknown"), FailureClass.TRANSIENT),
        (ValueError("bad json"), FailureClass.PERMANENT),
        (KeyError("missing"), FailureClass.PERMANENT),
        (MemoryError(), FailureClass.PERMANENT),
        (PermanentGenerationError("bad_payload"), FailureClass.PERMANENT),
    ],
)
def test_classify(error: BaseException, expected: FailureClass) -> None:
    """Scenario: A permanent failure parks the run with its reason"""
    assert classify(error, _never_provider) is expected


def test_provider_errors_are_transient_even_when_value_errors() -> None:
    """Scenario: A transient failure retries with backoff and jitter"""
    assert classify(ValueError("429"), lambda _exc: True) is FailureClass.TRANSIENT


def test_budget_error_keeps_its_code() -> None:
    """Scenario: A phase that keeps failing is parked once its budget is spent"""
    assert BudgetExhaustedError(ERROR_PHASE_BUDGET).error_code == ERROR_PHASE_BUDGET


def test_active_statuses() -> None:
    """Scenario: The same confirmation twice queues one run"""
    active = {status for status in GenerationStatus if is_active(status)}
    assert active == {
        GenerationStatus.QUEUED,
        GenerationStatus.RUNNING,
        GenerationStatus.RETRY_WAIT,
    }


def test_stage_commands_carry_their_dedupe_keys() -> None:
    """Scenario: The same confirmation twice queues one run"""
    drive = autopilot_stage("r9", "p9")
    assert drive.dedupe_key == "autopilot:r9"
    assert AutopilotDrivePayload.parse(drive.payload).autopilot_run_id == "r9"
    payload = WorkflowResumePayload(
        project_id="p1",
        action="revise",
        reviewer_id="u1",
        feedback="shorter",
        structured_feedback={"slides": [1]},
    )
    resume = resume_stage(payload, 7)
    assert resume.dedupe_key == "resume:p1:7"
    assert resume.carousel_project_id == "p1"
    assert WorkflowResumePayload.parse(resume.payload) == payload


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"project_id": "p", "action": "a", "reviewer_id": ""},
        {"project_id": "p", "action": "a", "reviewer_id": "u", "feedback": 3},
        {
            "project_id": "p",
            "action": "a",
            "reviewer_id": "u",
            "structured_feedback": [],
        },
    ],
)
def test_malformed_resume_payloads_are_refused(data: dict[str, object]) -> None:
    """Scenario: A permanent failure parks the run with its reason"""
    with pytest.raises(ValueError, match="invalid payload field"):
        WorkflowResumePayload.parse(data)
    with pytest.raises(ValueError, match="invalid payload field"):
        AutopilotDrivePayload.parse({"autopilot_run_id": 5})
