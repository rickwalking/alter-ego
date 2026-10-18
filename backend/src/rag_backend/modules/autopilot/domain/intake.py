"""Decide which scout proposals are stored and which are queued.

Pure: the caller supplies the allowlist, known hashes, recent carousel
topics, and how many runs were already created today. Persistence happens
in the application service.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import cast
from uuid import UUID, uuid4

from rag_backend.modules.autopilot.constants import (
    KIND_EXISTING,
    KIND_NEW,
    NO_QUEUE_SLOTS,
    REASON_DAILY_CAP_REACHED,
    REASON_DUPLICATE_TOPIC,
)
from rag_backend.modules.autopilot.domain.cover import CoverFacts
from rag_backend.modules.autopilot.domain.intake_proposal import (
    PreparedProposal,
    ProposalInput,
    prepare,
)
from rag_backend.modules.autopilot.domain.intake_rules import (
    Refusal,
    RuleFacts,
    TopicFields,
    refusal_for,
)
from rag_backend.modules.autopilot.domain.topic_text import (
    titles_are_duplicates,
)
from rag_backend.modules.autopilot.pov_constants import (
    MAX_NEWS_RUNS_PER_WEEK,
    REASON_WEEKLY_NEWS_CAP,
)


@dataclass(frozen=True, kw_only=True)
class IntakeFacts:
    """What the database knew before this batch was planned."""

    allowlist: frozenset[str]
    known_hashes: Mapping[str, UUID]
    carousel_topics: tuple[str, ...]
    runs_today: int
    daily_cap: int
    # AE-0377: Radar IA runs already created this São Paulo week.
    news_runs_this_week: int = 0
    # AE-0406: canonical status URL -> the post text stored through x-signals.
    post_texts: Mapping[str, str] = field(default_factory=dict)
    # AE-0418: the covers the batch names and the clock that ages them.
    covers: CoverFacts = field(default_factory=CoverFacts)


@dataclass(frozen=True, kw_only=True)
class TopicRejection:
    """One proposal the response lists under ``rejected``.

    AE-0406: ``index`` is its position in the request; ``field`` names the
    field that caused it, when one did.
    """

    title: str
    reason: str
    index: int = 0
    field: str | None = None


@dataclass(frozen=True, kw_only=True)
class NewCandidate:
    """A proposal this call will insert. ``queue`` is true when it gets a run."""

    candidate_id: UUID
    proposal: PreparedProposal
    queue: bool


@dataclass(frozen=True, kw_only=True)
class IntakePlan:
    """The persistence and response decisions for one batch."""

    accepted_ids: tuple[UUID, ...]
    new_candidates: tuple[NewCandidate, ...]
    rejected: tuple[TopicRejection, ...]


@dataclass(frozen=True, kw_only=True)
class _Classified:
    proposal: PreparedProposal
    kind: str
    candidate_id: UUID | None
    refusal: Refusal | None


def plan_intake(
    proposals: tuple[PreparedProposal, ...], facts: IntakeFacts
) -> IntakePlan:
    """Accept, reject, and mark the top scores that still fit today's cap."""
    memory = _Memory(known=dict(facts.known_hashes), claimed=set())
    rows = [_classify_and_remember(item, facts, memory) for item in proposals]
    return _finish(rows, facts)


@dataclass
class _Memory:
    """Hashes and (AE-0418) covers already taken by earlier topics of the batch."""

    known: dict[str, UUID]
    claimed: set[UUID]


def _classify_and_remember(
    proposal: PreparedProposal,
    facts: IntakeFacts,
    memory: _Memory,
) -> _Classified:
    claimed = replace(facts.covers, claimed=frozenset(memory.claimed))
    row = _classify(proposal, replace(facts, covers=claimed), memory.known)
    if row.kind == KIND_NEW and row.candidate_id is not None:
        memory.known[proposal.signal_hash] = row.candidate_id
        if proposal.cover_uuid is not None:
            memory.claimed.add(proposal.cover_uuid)
    return row


def _classify(
    proposal: PreparedProposal,
    facts: IntakeFacts,
    known: Mapping[str, UUID],
) -> _Classified:
    refusal = _refusal(proposal, facts)
    if refusal is not None:
        return _Classified(
            proposal=proposal,
            kind=KIND_NEW,
            candidate_id=None,
            refusal=refusal,
        )
    existing = known.get(proposal.signal_hash)
    if existing is not None:
        return _Classified(
            proposal=proposal,
            kind=KIND_EXISTING,
            candidate_id=existing,
            refusal=None,
        )
    if _matches_recent_topic(proposal.title, facts.carousel_topics):
        return _Classified(
            proposal=proposal,
            kind=KIND_NEW,
            candidate_id=None,
            refusal=Refusal(reason=REASON_DUPLICATE_TOPIC),
        )
    return _Classified(
        proposal=proposal,
        kind=KIND_NEW,
        candidate_id=uuid4(),
        refusal=None,
    )


def _refusal(proposal: PreparedProposal, facts: IntakeFacts) -> Refusal | None:
    return refusal_for(
        TopicFields(
            title=proposal.title,
            angle=proposal.angle,
            why_viral=proposal.why_viral,
            audience=proposal.audience,
            niche=proposal.niche,
            brief=proposal.brief,
            sources=proposal.sources,
            image_style=proposal.image_style,
            image_guidance=proposal.image_guidance,
            content_mode=proposal.content_mode,
            thesis_draft=proposal.thesis_draft,
            quotes=proposal.quotes,
            cover_asset_id=proposal.cover_asset_id,
        ),
        RuleFacts(
            allowlist=facts.allowlist,
            post_texts=facts.post_texts,
            covers=facts.covers,
        ),
    )


def _matches_recent_topic(title: str, topics: tuple[str, ...]) -> bool:
    return any(titles_are_duplicates(title, topic) for topic in topics)


@dataclass
class _Buckets:
    """Mutable accumulators for one planning pass."""

    accepted: list[UUID]
    fresh: list[_Classified]
    rejected: list[TopicRejection]
    seen: set[UUID]


def _finish(rows: list[_Classified], facts: IntakeFacts) -> IntakePlan:
    buckets = _Buckets(accepted=[], fresh=[], rejected=[], seen=set())
    for row in rows:
        _collect_row(row, buckets)
    queue_ids = _ids_to_queue(buckets.fresh, facts)
    if _slots(facts) == NO_QUEUE_SLOTS:
        buckets.rejected.extend(_rejections(buckets.fresh, REASON_DAILY_CAP_REACHED))
    else:
        buckets.rejected.extend(_weekly_cap_rejections(buckets.fresh, facts))
    candidates = tuple(_candidate(row, queue_ids) for row in buckets.fresh)
    return IntakePlan(
        accepted_ids=tuple(buckets.accepted),
        new_candidates=candidates,
        rejected=tuple(buckets.rejected),
    )


def _collect_row(row: _Classified, buckets: _Buckets) -> None:
    if row.refusal is not None:
        buckets.rejected.append(rejection(row.proposal, row.refusal))
        return
    if row.candidate_id is None or row.candidate_id in buckets.seen:
        return
    buckets.seen.add(row.candidate_id)
    buckets.accepted.append(row.candidate_id)
    if row.kind == KIND_NEW:
        buckets.fresh.append(row)


def rejection(proposal: PreparedProposal, refusal: Refusal) -> TopicRejection:
    """The response row for a refused proposal (title, index and field)."""
    return TopicRejection(
        title=_rejection_title(proposal),
        reason=refusal.reason,
        index=proposal.index,
        field=refusal.field,
    )


def _rejection_title(proposal: PreparedProposal) -> str:
    if proposal.title != "":
        return proposal.title
    return proposal.raw_title


def _slots(facts: IntakeFacts) -> int:
    room = facts.daily_cap - facts.runs_today
    if room < NO_QUEUE_SLOTS:
        return NO_QUEUE_SLOTS
    return room


def _ids_to_queue(fresh: list[_Classified], facts: IntakeFacts) -> frozenset[UUID]:
    room = _slots(facts)
    if room == NO_QUEUE_SLOTS:
        return frozenset()
    ranked = _within_news_cap(sorted(fresh, key=_score, reverse=True), facts)
    return frozenset(_required_ids(ranked[:room]))


def _within_news_cap(
    ranked: list[_Classified], facts: IntakeFacts
) -> list[_Classified]:
    """AE-0377: queue at most the week's remaining Radar IA runs (POV is free).

    AE-0406: ``pov_news`` is POV here: it counts toward the daily cap only.
    """
    news_left = MAX_NEWS_RUNS_PER_WEEK - facts.news_runs_this_week
    kept: list[_Classified] = []
    for row in ranked:
        if row.proposal.is_news:
            if news_left <= 0:
                continue
            news_left -= 1
        kept.append(row)
    return kept


def _score(row: _Classified) -> int:
    return row.proposal.score


def _required_ids(rows: list[_Classified]) -> list[UUID]:
    return [row.candidate_id for row in rows if row.candidate_id is not None]


def _rejections(rows: Iterable[_Classified], reason: str) -> list[TopicRejection]:
    return [rejection(row.proposal, Refusal(reason=reason)) for row in rows]


def _weekly_cap_rejections(
    fresh: list[_Classified], facts: IntakeFacts
) -> list[TopicRejection]:
    """AE-0377: Radar IA topics stored but not queued (this week's run is used)."""
    if facts.news_runs_this_week < MAX_NEWS_RUNS_PER_WEEK:
        return []
    news = (row for row in fresh if row.proposal.is_news)
    return _rejections(news, REASON_WEEKLY_NEWS_CAP)


def _candidate(row: _Classified, queue_ids: frozenset[UUID]) -> NewCandidate:
    candidate_id = cast(UUID, row.candidate_id)
    return NewCandidate(
        candidate_id=candidate_id,
        proposal=row.proposal,
        queue=candidate_id in queue_ids,
    )


__all__ = [
    "IntakeFacts",
    "IntakePlan",
    "NewCandidate",
    "PreparedProposal",
    "ProposalInput",
    "TopicRejection",
    "plan_intake",
    "prepare",
    "rejection",
]
