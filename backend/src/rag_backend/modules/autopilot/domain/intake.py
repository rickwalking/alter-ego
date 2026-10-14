"""Decide which scout proposals are stored and which are queued.

Pure: the caller supplies the allowlist, known hashes, recent carousel
topics, and how many runs were already created today. Persistence happens
in the application service.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast
from uuid import UUID, uuid4

from rag_backend.modules.autopilot.constants import (
    KIND_EXISTING,
    KIND_NEW,
    NO_QUEUE_SLOTS,
    REASON_DAILY_CAP_REACHED,
    REASON_DUPLICATE_TOPIC,
    REASON_EMPTY_TEXT,
    REASON_SOURCE_NOT_IN_SIGNALS,
    REASON_URL_IN_TEXT,
)
from rag_backend.modules.autopilot.domain.carousel_defaults import (
    DEFAULT_IMAGE_STYLE,
    CarouselText,
    carousel_reason,
)
from rag_backend.modules.autopilot.domain.topic_text import (
    contains_url,
    signal_hash,
    strip_controls,
    titles_are_duplicates,
)
from rag_backend.modules.autopilot.domain.x_status import canonical_url


@dataclass(frozen=True, kw_only=True)
class ProposalInput:
    """One schema-valid proposal before control-character stripping."""

    title: str
    angle: str
    why_viral: str
    audience: str
    niche: str
    brief: str
    sources: tuple[str, ...]
    score: int
    image_style: str = DEFAULT_IMAGE_STYLE
    image_guidance: str | None = None


@dataclass(frozen=True, kw_only=True)
class PreparedProposal:
    """A proposal after stripping and canonicalizing sources."""

    raw_title: str
    title: str
    angle: str
    why_viral: str
    audience: str
    niche: str
    brief: str
    sources: tuple[str, ...]
    score: int
    signal_hash: str
    image_style: str = DEFAULT_IMAGE_STYLE
    image_guidance: str | None = None


@dataclass(frozen=True, kw_only=True)
class IntakeFacts:
    """What the database knew before this batch was planned."""

    allowlist: frozenset[str]
    known_hashes: Mapping[str, UUID]
    carousel_topics: tuple[str, ...]
    runs_today: int
    daily_cap: int


@dataclass(frozen=True, kw_only=True)
class TopicRejection:
    """One proposal the response lists under ``rejected``."""

    title: str
    reason: str


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
    reason: str | None


def prepare(proposal: ProposalInput) -> PreparedProposal:
    """Strip control characters and canonicalize source URLs."""
    title = strip_controls(proposal.title)
    sources = tuple(
        canonical_url(strip_controls(source)) for source in proposal.sources
    )
    return PreparedProposal(
        raw_title=proposal.title,
        title=title,
        angle=strip_controls(proposal.angle),
        why_viral=strip_controls(proposal.why_viral),
        audience=strip_controls(proposal.audience),
        niche=strip_controls(proposal.niche),
        brief=strip_controls(proposal.brief),
        sources=sources,
        score=proposal.score,
        signal_hash=signal_hash(title, sources),
        image_style=proposal.image_style,
        image_guidance=_optional_text(proposal.image_guidance),
    )


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return strip_controls(value) or None


def plan_intake(
    proposals: tuple[PreparedProposal, ...], facts: IntakeFacts
) -> IntakePlan:
    """Accept, reject, and mark the top scores that still fit today's cap."""
    known = dict(facts.known_hashes)
    rows = [_classify_and_remember(item, facts, known) for item in proposals]
    return _finish(rows, facts)


def _classify_and_remember(
    proposal: PreparedProposal,
    facts: IntakeFacts,
    known: dict[str, UUID],
) -> _Classified:
    row = _classify(proposal, facts, known)
    if row.kind == KIND_NEW and row.candidate_id is not None:
        known[proposal.signal_hash] = row.candidate_id
    return row


def _classify(
    proposal: PreparedProposal,
    facts: IntakeFacts,
    known: Mapping[str, UUID],
) -> _Classified:
    reason = _rejection_reason(proposal, facts)
    if reason is not None:
        return _Classified(
            proposal=proposal,
            kind=KIND_NEW,
            candidate_id=None,
            reason=reason,
        )
    existing = known.get(proposal.signal_hash)
    if existing is not None:
        return _Classified(
            proposal=proposal,
            kind=KIND_EXISTING,
            candidate_id=existing,
            reason=None,
        )
    if _matches_recent_topic(proposal.title, facts.carousel_topics):
        return _Classified(
            proposal=proposal,
            kind=KIND_NEW,
            candidate_id=None,
            reason=REASON_DUPLICATE_TOPIC,
        )
    return _Classified(
        proposal=proposal,
        kind=KIND_NEW,
        candidate_id=uuid4(),
        reason=None,
    )


def _rejection_reason(proposal: PreparedProposal, facts: IntakeFacts) -> str | None:
    if _is_blank(proposal):
        return REASON_EMPTY_TEXT
    if _text_has_url(proposal):
        return REASON_URL_IN_TEXT
    if _missing_source(proposal, facts.allowlist):
        return REASON_SOURCE_NOT_IN_SIGNALS
    return carousel_reason(_carousel_text(proposal))


def _carousel_text(proposal: PreparedProposal) -> CarouselText:
    return CarouselText(
        title=proposal.title,
        audience=proposal.audience,
        niche=proposal.niche,
        brief=proposal.brief,
        image_style=proposal.image_style,
    )


def _free_text(proposal: PreparedProposal) -> tuple[str, ...]:
    return (
        proposal.title,
        proposal.angle,
        proposal.why_viral,
        proposal.audience,
        proposal.niche,
        proposal.brief,
    )


def _is_blank(proposal: PreparedProposal) -> bool:
    return any(text == "" for text in _free_text(proposal))


def _text_has_url(proposal: PreparedProposal) -> bool:
    texts = (*_free_text(proposal), proposal.image_guidance or "")
    return any(contains_url(text) for text in texts)


def _missing_source(proposal: PreparedProposal, allowlist: frozenset[str]) -> bool:
    return any(source not in allowlist for source in proposal.sources)


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
        buckets.rejected.extend(_cap_rejections(buckets.fresh))
    candidates = tuple(_candidate(row, queue_ids) for row in buckets.fresh)
    return IntakePlan(
        accepted_ids=tuple(buckets.accepted),
        new_candidates=candidates,
        rejected=tuple(buckets.rejected),
    )


def _collect_row(row: _Classified, buckets: _Buckets) -> None:
    if row.reason is not None:
        buckets.rejected.append(
            TopicRejection(title=_rejection_title(row.proposal), reason=row.reason)
        )
        return
    if row.candidate_id is None or row.candidate_id in buckets.seen:
        return
    buckets.seen.add(row.candidate_id)
    buckets.accepted.append(row.candidate_id)
    if row.kind == KIND_NEW:
        buckets.fresh.append(row)


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
    ranked = sorted(fresh, key=_score, reverse=True)
    return frozenset(_required_ids(ranked[:room]))


def _score(row: _Classified) -> int:
    return row.proposal.score


def _required_ids(rows: list[_Classified]) -> list[UUID]:
    return [row.candidate_id for row in rows if row.candidate_id is not None]


def _cap_rejections(fresh: list[_Classified]) -> list[TopicRejection]:
    return [
        TopicRejection(
            title=_rejection_title(row.proposal),
            reason=REASON_DAILY_CAP_REACHED,
        )
        for row in fresh
    ]


def _candidate(row: _Classified, queue_ids: frozenset[UUID]) -> NewCandidate:
    candidate_id = cast(UUID, row.candidate_id)
    return NewCandidate(
        candidate_id=candidate_id,
        proposal=row.proposal,
        queue=candidate_id in queue_ids,
    )
