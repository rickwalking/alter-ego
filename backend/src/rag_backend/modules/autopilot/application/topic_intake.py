"""Accept a scout topic batch: store candidates and queue within the daily cap.

The unit of work commits once, after every insert for the batch. A second
post of the same signal hash does not create another run.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

import structlog

from rag_backend.modules.autopilot.constants import (
    LOG_TOPIC_INTAKE,
    REASON_DUPLICATE_TOPIC,
    STATUS_CANDIDATE_ACCEPTED,
)
from rag_backend.modules.autopilot.domain.intake import (
    IntakeFacts,
    IntakePlan,
    NewCandidate,
    PreparedProposal,
    ProposalInput,
    TopicRejection,
    plan_intake,
    prepare,
)
from rag_backend.modules.autopilot.domain.models import TopicCandidate
from rag_backend.modules.autopilot.domain.ports import (
    Clock,
    DayWindow,
    HashLookup,
    QueuedRunCommand,
    TopicIntakeStore,
)
from rag_backend.modules.autopilot.domain.pov_schedule import sao_paulo_week
from rag_backend.modules.autopilot.domain.topic_text import (
    carousel_topic_cutoff,
    sao_paulo_day,
    served_url_cutoff,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class TopicIntakeDependencies:
    """Collaborators for one intake call. One object keeps the constructor small."""

    store: TopicIntakeStore
    clock: Clock
    daily_cap: int


@dataclass(frozen=True, kw_only=True)
class TopicIntakeCommand:
    """The schema-valid proposals from one POST."""

    proposals: tuple[ProposalInput, ...]


@dataclass(frozen=True, kw_only=True)
class TopicIntakeResult:
    """Ids stored, runs created, and proposals the response rejects."""

    accepted: tuple[UUID, ...]
    queued: tuple[UUID, ...]
    rejected: tuple[TopicRejection, ...]


class TopicIntakeService:
    """Plan a batch against the database and persist the decision."""

    def __init__(self, deps: TopicIntakeDependencies) -> None:
        self._deps = deps

    async def accept(self, command: TopicIntakeCommand) -> TopicIntakeResult:
        """Store every accepted proposal and queue only those the cap allows."""
        prepared = tuple(prepare(item) for item in command.proposals)
        await self._deps.store.lock_intake()
        facts = await self._facts(prepared)
        plan = await self._stored(plan_intake(prepared, facts))
        queued = await self._queue(plan)
        await self._deps.store.commit()
        result = TopicIntakeResult(
            accepted=plan.accepted_ids,
            queued=queued,
            rejected=plan.rejected,
        )
        _log(result)
        return result

    async def _facts(self, prepared: tuple[PreparedProposal, ...]) -> IntakeFacts:
        now = self._deps.clock.now()
        start, end = sao_paulo_day(now)
        store = self._deps.store
        hashes = tuple(item.signal_hash for item in prepared)
        allowlist = await store.urls_served_since(served_url_cutoff(now))
        known_hashes = await store.ids_for_hashes(HashLookup(hashes=hashes))
        topics = await store.carousel_topics_since(carousel_topic_cutoff(now))
        runs_today = await store.runs_created_between(DayWindow(start=start, end=end))
        week_start, week_end = sao_paulo_week(now)
        news_week = await store.news_runs_created_between(
            DayWindow(start=week_start, end=week_end)
        )
        return IntakeFacts(
            allowlist=allowlist,
            known_hashes=known_hashes,
            carousel_topics=topics,
            runs_today=runs_today,
            daily_cap=self._deps.daily_cap,
            news_runs_this_week=news_week,
        )

    async def _stored(self, plan: IntakePlan) -> IntakePlan:
        """Insert new candidates. A hash a concurrent batch won is a duplicate."""
        kept: list[NewCandidate] = []
        lost: list[NewCandidate] = []
        for item in plan.new_candidates:
            stored = await self._deps.store.add_candidate(_candidate(item))
            (kept if stored else lost).append(item)
        if not lost:
            return plan
        lost_ids = {item.candidate_id for item in lost}
        # A lost row is a duplicate, not also "capped" (daily or weekly).
        lost_titles = {item.proposal.title for item in lost}
        capped = tuple(r for r in plan.rejected if r.title not in lost_titles)
        return IntakePlan(
            accepted_ids=tuple(i for i in plan.accepted_ids if i not in lost_ids),
            new_candidates=tuple(kept),
            rejected=(*capped, *(_duplicate(item) for item in lost)),
        )

    async def _queue(self, plan: IntakePlan) -> tuple[UUID, ...]:
        created_at = self._deps.clock.now()
        ranked = sorted(plan.new_candidates, key=_score, reverse=True)
        queued: list[UUID] = []
        for item in ranked:
            run_id = await self._queue_one(item, created_at)
            if run_id is not None:
                queued.append(run_id)
        return tuple(queued)

    async def _queue_one(self, item: NewCandidate, created_at: datetime) -> UUID | None:
        if not item.queue:
            return None
        run_id = uuid4()
        await self._deps.store.add_queued_run(
            QueuedRunCommand(
                run_id=run_id,
                topic_candidate_id=item.candidate_id,
                created_at=created_at,
            )
        )
        return run_id


def _candidate(item: NewCandidate) -> TopicCandidate:
    proposal = item.proposal
    return TopicCandidate(
        candidate_id=item.candidate_id,
        title=proposal.title,
        angle=proposal.angle,
        why_viral=proposal.why_viral,
        audience=proposal.audience,
        niche=proposal.niche,
        brief=proposal.brief,
        sources=proposal.sources,
        score=proposal.score,
        signal_hash=proposal.signal_hash,
        status=STATUS_CANDIDATE_ACCEPTED,
        image_style=proposal.image_style,
        image_guidance=proposal.image_guidance,
        content_mode=proposal.content_mode,
        thesis_draft=proposal.thesis_draft,
    )


def _duplicate(item: NewCandidate) -> TopicRejection:
    return TopicRejection(title=item.proposal.title, reason=REASON_DUPLICATE_TOPIC)


def _score(item: NewCandidate) -> int:
    return item.proposal.score


def _log(result: TopicIntakeResult) -> None:
    logger.info(
        LOG_TOPIC_INTAKE,
        accepted=len(result.accepted),
        queued=len(result.queued),
        rejected=len(result.rejected),
    )
