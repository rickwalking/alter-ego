"""Promote waiting backlog themes into today's free slots, without a scout batch.

The generation worker runs this every morning at 08:05 São Paulo time, so themes
that waited for the next morning start even on a day no batch arrives. It takes
the same intake lock as a scout batch and counts today's runs first, so a second
run (or a batch that already used the slots) promotes nothing more.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.autopilot.application.intake_backlog import IntakeBacklog
from rag_backend.modules.autopilot.domain.backlog import BacklogStore
from rag_backend.modules.autopilot.domain.intake import IntakeFacts
from rag_backend.modules.autopilot.domain.ports import (
    Clock,
    DayWindow,
    TopicIntakeStore,
)
from rag_backend.modules.autopilot.domain.topic_text import sao_paulo_day


@dataclass(frozen=True, kw_only=True)
class PromotionDependencies:
    """Ports bound to one transaction, and the daily cap."""

    store: TopicIntakeStore
    backlog: BacklogStore
    clock: Clock
    daily_cap: int


async def promote_waiting(deps: PromotionDependencies) -> int:
    """Queue the oldest waiting themes that fit today; commit; how many were queued."""
    await deps.store.lock_intake()
    now = deps.clock.now()
    start, end = sao_paulo_day(now)
    runs_today = await deps.store.runs_created_between(DayWindow(start=start, end=end))
    facts = IntakeFacts(
        allowlist=frozenset(),
        known_hashes={},
        carousel_topics=(),
        runs_today=runs_today,
        daily_cap=deps.daily_cap,
    )
    promotion = await IntakeBacklog(deps.backlog, deps.store).promote(facts, now)
    await deps.store.commit()
    return len(promotion.run_ids)


__all__ = ["PromotionDependencies", "promote_waiting"]
