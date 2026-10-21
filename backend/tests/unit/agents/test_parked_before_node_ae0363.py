"""Which checkpoints a re-drive may continue.

Gherkin: tests/features/autopilot_runner.feature
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.agents.carousel_workflow_engine import is_parked_before_node
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_APPROVED_HOLD,
    PHASE_CONTENT,
)


@dataclass(frozen=True)
class _Task:
    interrupts: tuple[object, ...] = ()


@dataclass(frozen=True)
class _Snapshot:
    next: tuple[str, ...] = ()
    interrupts: tuple[object, ...] = ()
    tasks: tuple[_Task, ...] = ()


def test_pending_node_without_interrupt_is_parked() -> None:
    """Scenario: carousel 8e350d6e (next=content, no interrupt) is parked."""
    assert is_parked_before_node(_Snapshot(next=(PHASE_CONTENT,), tasks=(_Task(),)))


def test_nothing_pending_or_a_human_gate_is_not_parked() -> None:
    assert not is_parked_before_node(None)
    assert not is_parked_before_node(_Snapshot())
    assert not is_parked_before_node(
        _Snapshot(next=(PHASE_CONTENT,), interrupts=("gate",))
    )
    assert not is_parked_before_node(
        _Snapshot(next=(PHASE_CONTENT,), tasks=(_Task(interrupts=("gate",)),))
    )


def test_approved_hold_is_a_held_carousel_not_a_dead_run() -> None:
    assert not is_parked_before_node(_Snapshot(next=(PHASE_APPROVED_HOLD,)))
