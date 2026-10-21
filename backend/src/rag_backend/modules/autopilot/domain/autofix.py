"""The owner "Fix issues" port. Pure data and a protocol.

``inspect`` is cheap and read-only (the webhook and the review message call
it); ``autofix`` repairs, re-translates untranslated EN and re-renders, so
only the worker tick calls it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class AutofixStatus(StrEnum):
    """Outcome of one autofix.

    ``CONFLICT``: another writer held the project lock or moved the lock version.
    """

    FIXED = "fixed"
    NOTHING_TO_FIX = "nothing_to_fix"
    CONFLICT = "conflict"


@dataclass(frozen=True, kw_only=True)
class QualityIssues:
    """Issue lines for the review message; ``fixable`` shows the button."""

    lines: tuple[str, ...] = ()
    fixable: bool = False


@dataclass(frozen=True, kw_only=True)
class AutofixCommand:
    """Fix one carousel at the workflow lock version the tick read."""

    project_id: str
    expected_version: int


@dataclass(frozen=True, kw_only=True)
class AutofixOutcome:
    """What the fix did and what is left for a rework."""

    status: AutofixStatus
    remaining: tuple[str, ...] = ()
    translation_failed: bool = False


class ContentAutofixer(Protocol):
    """In-process editorial content repair. No HTTP."""

    async def inspect(self, project_id: str) -> QualityIssues:
        """Issue lines and fixability. No LLM, no writes."""
        ...

    async def autofix(self, command: AutofixCommand) -> AutofixOutcome:
        """Repair, re-translate untranslated EN, persist and re-render once."""
        ...


@dataclass(frozen=True, kw_only=True)
class GateRepairCommand:
    """Repair one gate's checkpoint copy at the lock version the tick read."""

    project_id: str
    expected_version: int
    phase: str


@dataclass(frozen=True, kw_only=True)
class GateRepairOutcome:
    """What the gate repair fixed and which blocking rules are left."""

    status: AutofixStatus
    fixed_rules: tuple[str, ...] = ()
    remaining_rules: tuple[str, ...] = ()


class GateRepairer(Protocol):
    """Deterministic repair of a content/design gate before a revise."""

    async def repair_gate(self, command: GateRepairCommand) -> GateRepairOutcome:
        """Repair the checkpoint copy and re-validate. No re-render."""
        ...


@dataclass(frozen=True, kw_only=True)
class SlideFixCommand:
    """Model-fix one gate's failing slides at the lock version the tick read."""

    project_id: str
    expected_version: int
    phase: str


@dataclass(frozen=True, kw_only=True)
class SlideFixAttemptRecord:
    """One model attempt on one slide, for the per-attempt log.

    ``model_role`` is the model role of the attempt (``fast`` or ``reasoning``).
    """

    slide_index: int
    attempt: int
    rules_before: tuple[str, ...]
    rules_after: tuple[str, ...]
    outcome: str
    model_role: str = ""


@dataclass(frozen=True, kw_only=True)
class FailingSlide:
    """A slide the model fix gave up on: its rules, its text, its attempts."""

    slide_index: int
    rules: tuple[str, ...]
    text: str
    attempts: int


@dataclass(frozen=True, kw_only=True)
class SlideFixOutcome:
    """What the model fix wrote and which slides are still failing.

    ``unscored_slides`` passed every rule but the judge gave no
    score (a re-score is pending); ``judge_unavailable`` is set once one of
    them stayed unscored for the configured number of ticks.
    """

    status: AutofixStatus
    failing: tuple[FailingSlide, ...] = ()
    attempts: tuple[SlideFixAttemptRecord, ...] = ()
    unfixable_rules: tuple[str, ...] = ()
    unscored_slides: tuple[int, ...] = ()
    judge_unavailable: bool = False


class SlideFixer(Protocol):
    """Model fix of the slides still failing after the repair."""

    async def fix_slides(self, command: SlideFixCommand) -> SlideFixOutcome:
        """Rewrite each failing slide (N attempts), persist the fixed ones."""
        ...
