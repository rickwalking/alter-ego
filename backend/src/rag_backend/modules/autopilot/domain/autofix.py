"""The owner "Fix issues" port (AE-0367). Pure data and a protocol.

``inspect`` is cheap and read-only (the webhook and the review message call
it); ``autofix`` repairs, re-translates untranslated EN and re-renders, so
only the worker tick calls it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class AutofixStatus(StrEnum):
    """Outcome of one autofix."""

    FIXED = "fixed"
    NOTHING_TO_FIX = "nothing_to_fix"
    # Another writer held the project lock or moved the lock version.
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
