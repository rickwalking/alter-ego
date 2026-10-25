"""The backlog side of topic intake: promote waiting themes, keep the overflow.

Before a scout batch is planned, the day's free slots go to themes from earlier
days, oldest first. After the plan, new themes the cap left out join the backlog
(best score first) until ``BACKLOG_MAX`` themes wait; the rest are refused as
``backlog_full``. Radar IA topics never join it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from rag_backend.modules.autopilot.constants import STATUS_CANDIDATE_ACCEPTED
from rag_backend.modules.autopilot.domain.backlog import (
    BacklogChange,
    BacklogStore,
    BacklogWindow,
    backlog_room,
    expiry_cutoff,
    promotable,
)
from rag_backend.modules.autopilot.domain.intake import (
    IntakeFacts,
    IntakePlan,
    NewCandidate,
    TopicRejection,
)
from rag_backend.modules.autopilot.domain.ports import (
    QueuedRunCommand,
    TopicIntakeStore,
)
from rag_backend.modules.autopilot.domain.topic_text import sao_paulo_day
from rag_backend.modules.autopilot.queue_constants import (
    CANDIDATE_BACKLOG,
    CANDIDATE_PROMOTED,
    REASON_BACKLOG_FULL,
)


@dataclass(frozen=True, kw_only=True)
class Promotion:
    """Runs queued for backlog themes, and how many themes were waiting."""

    run_ids: tuple[UUID, ...]
    waiting_count: int


class IntakeBacklog:
    """Promote and keep backlog themes for one intake call."""

    def __init__(self, backlog: BacklogStore, store: TopicIntakeStore) -> None:
        self._backlog = backlog
        self._store = store

    async def promote(self, facts: IntakeFacts, now: datetime) -> Promotion:
        """Queue the oldest themes from earlier days that fit today's slots."""
        cutoff = expiry_cutoff(now)
        day_start, _ = sao_paulo_day(now)
        alive = await self._backlog.waiting(BacklogWindow(since=cutoff, before=now))
        earlier = [theme for theme in alive if theme.created_at < day_start]
        wanted = promotable(earlier, facts.daily_cap - facts.runs_today)
        ids = await self._backlog.change(
            BacklogChange(candidate_ids=wanted, status=CANDIDATE_PROMOTED)
        )
        run_ids: list[UUID] = []
        for candidate_id in ids:
            run_id = uuid4()
            await self._store.add_queued_run(
                QueuedRunCommand(
                    run_id=run_id, topic_candidate_id=candidate_id, created_at=now
                )
            )
            run_ids.append(run_id)
        return Promotion(run_ids=tuple(run_ids), waiting_count=len(alive))

    async def keep_overflow(
        self, plan: IntakePlan, promotion: Promotion
    ) -> tuple[TopicRejection, ...]:
        """Park the themes the cap left out; the refusals for a full backlog."""
        overflow = sorted(
            (c for c in plan.new_candidates if not c.queue and not c.proposal.is_news),
            key=_score,
            reverse=True,
        )
        room = backlog_room(promotion.waiting_count, len(promotion.run_ids))
        kept = tuple(item.candidate_id for item in overflow[:room])
        await self._backlog.change(
            BacklogChange(
                candidate_ids=kept,
                status=CANDIDATE_BACKLOG,
                expected=(STATUS_CANDIDATE_ACCEPTED,),
            )
        )
        return tuple(_full(item) for item in overflow[room:])


def merge_rejections(
    rejected: tuple[TopicRejection, ...], full: tuple[TopicRejection, ...]
) -> tuple[TopicRejection, ...]:
    """A theme refused for a full backlog is reported once, as ``backlog_full``."""
    refused = {item.index for item in full}
    return (*(r for r in rejected if r.index not in refused), *full)


def _full(item: NewCandidate) -> TopicRejection:
    return TopicRejection(
        title=item.proposal.title,
        reason=REASON_BACKLOG_FULL,
        index=item.proposal.index,
    )


def _score(item: NewCandidate) -> int:
    return item.proposal.score


__all__ = ["IntakeBacklog", "Promotion", "merge_rejections"]
