"""Publish claims: one caller at a time talks to Graph (QA r1 H1).

A run claim is a compare-and-set on ``publish_claimed_at``; a manual claim
is one row per carousel in ``instagram_manual_publishes``. Both are
committed at once, so the worker and the manual route see each other. A
claim older than the stale window is taken over (the holder crashed).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class RunClaim:
    """Claim a ``publishing`` run unless a fresh claim is held."""

    run_id: UUID
    now: datetime
    stale_before: datetime


@dataclass(frozen=True, kw_only=True)
class ManualClaim:
    """Claim a carousel without an autopilot run for one manual publish."""

    project_id: str
    now: datetime
    stale_before: datetime


@dataclass(frozen=True, kw_only=True)
class ManualRecord:
    """The stored manual publish for one carousel."""

    project_id: str
    state: str
    ig_post_id: str | None
    ig_permalink: str | None
    error: str | None


class PublishClaims(Protocol):
    """Claim, release, and record. Every write is committed by the adapter."""

    async def claim_run(self, claim: RunClaim) -> bool:
        """True when this caller now holds the run's publish claim."""
        ...

    async def release_run(self, run_id: UUID) -> None:
        """Drop the run claim."""
        ...

    async def manual_record(self, project_id: str) -> ManualRecord | None:
        """The stored manual publish for the carousel, if any."""
        ...

    async def claim_manual(self, claim: ManualClaim) -> bool:
        """True when this caller now holds the carousel's manual claim."""
        ...

    async def finish_manual(self, record: ManualRecord) -> None:
        """Store the outcome and release the manual claim."""
        ...
