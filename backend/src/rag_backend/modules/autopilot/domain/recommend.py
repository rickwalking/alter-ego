"""Recommended publish slots (AE-0404). Pure, no I/O.

A candidate slot is a São Paulo day at a whole hour of ``CANDIDATE_HOURS``.
Its score blends the audience (followers online at that UTC hour), the
engagement of our posts published in the same (weekday, hour) bucket, shrunk
by the bucket's post count, and the editorial prior. See
``recommend_constants`` for the weights.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.domain.pov_schedule import (
    POV_SLOT_TIME,
    POV_SLOT_WEEKDAYS,
)
from rag_backend.modules.autopilot.domain.schedule import (
    check_choice,
    schedule_zone,
)
from rag_backend.modules.autopilot.recommend_constants import (
    CANDIDATE_HOURS,
    MAX_STARRED_DAYS,
    PICKER_DAYS,
    PRIOR_PLAN,
    PRIOR_SECONDARY,
    REASON_ALTERNATIVE,
    REASON_AUDIENCE,
    REASON_DEFAULT_SLOT,
    REASON_PERFORMANCE,
    REASON_POV_PLAN,
    SHRINKAGE_POSTS,
    STARRED_DAY_SHARE,
    TEXT_REASON_ALTERNATIVE,
    TEXT_REASON_AUDIENCE,
    TEXT_REASON_DEFAULT_SLOT,
    TEXT_REASON_PERFORMANCE,
    TEXT_REASON_POV_PLAN,
    TOP_TIMES_PER_DAY,
    WEIGHT_AUDIENCE,
    WEIGHT_PERFORMANCE,
    WEIGHT_PRIOR,
)
from rag_backend.modules.autopilot.schedule_constants import (
    SCHEDULE_MIN_LEAD_MINUTES,
    SCHEDULE_SLOTS,
    TIME_SEPARATOR,
)

_WEIGHT_TOTAL = WEIGHT_PRIOR + WEIGHT_AUDIENCE + WEIGHT_PERFORMANCE
_SCORE_DIGITS = 6
_Bucket = tuple[int, int]


@dataclass(frozen=True, kw_only=True)
class PostEngagement:
    """One published post: when it went out and its engagement rate."""

    published_at: datetime
    rate: float


@dataclass(frozen=True, kw_only=True)
class ScheduleSignals:
    """Audience (followers online per UTC hour) and post engagement."""

    audience: Mapping[int, int] = field(default_factory=dict)
    posts: tuple[PostEngagement, ...] = ()


@dataclass(frozen=True, kw_only=True)
class RecommendQuery:
    """Rank slots for one run at ``now``. ``pov`` selects the POV prior."""

    now: datetime
    pov: bool
    signals: ScheduleSignals


@dataclass(frozen=True, kw_only=True)
class ScoredSlot:
    """A slot (UTC), its blended score, and why it scored."""

    at: datetime
    score: float
    reason: str
    posts: int = 0


@dataclass(frozen=True, kw_only=True)
class DayOption:
    """One day of the picker; ``starred`` marks the best days."""

    day: date
    starred: bool


@dataclass(frozen=True, kw_only=True)
class _Parts:
    prior: float
    audience: float
    performance: float
    posts: int
    prior_reason: str


def engagement_rate(metrics: InsightMetrics) -> float | None:
    """``(saved + shares + total_interactions) / reach``; None without reach."""
    if not metrics.reach:
        return None
    engaged = (metrics.saved or 0) + (metrics.shares or 0)
    return (engaged + (metrics.total_interactions or 0)) / metrics.reach


def score_slot(query: RecommendQuery, at: datetime) -> ScoredSlot:
    """Score one moment (a picker slot or an owner-typed time)."""
    return _score(_Scorer(query), at)


def _score(scorer: _Scorer, at: datetime) -> ScoredSlot:
    parts = scorer.parts(at)
    contributions = {
        REASON_PERFORMANCE: WEIGHT_PERFORMANCE * parts.performance,
        REASON_AUDIENCE: WEIGHT_AUDIENCE * parts.audience,
        parts.prior_reason: WEIGHT_PRIOR * parts.prior,
    }
    total = sum(contributions.values())
    reason = max(contributions, key=lambda key: contributions[key])
    if total <= 0:
        reason = REASON_ALTERNATIVE
    score = round(total / _WEIGHT_TOTAL, _SCORE_DIGITS)
    return ScoredSlot(at=at, score=score, reason=reason, posts=parts.posts)


def slots_on(query: RecommendQuery, day: date) -> tuple[ScoredSlot, ...]:
    """The day's open slots, best first (ties: closest to a default slot)."""
    zone = schedule_zone()
    earliest = query.now + timedelta(minutes=SCHEDULE_MIN_LEAD_MINUTES)
    scorer = _Scorer(query)
    found = []
    for hour in CANDIDATE_HOURS:
        at = datetime.combine(day, time(hour, 0), tzinfo=zone).astimezone(UTC)
        if at >= earliest and check_choice(at, query.now) is None:
            found.append(_score(scorer, at))
    return tuple(sorted(found, key=_rank_key))


def top_times(query: RecommendQuery, day: date) -> tuple[ScoredSlot, ...]:
    """The day's best ``TOP_TIMES_PER_DAY`` slots, best first."""
    return slots_on(query, day)[:TOP_TIMES_PER_DAY]


def picker_days(query: RecommendQuery) -> tuple[DayOption, ...]:
    """Seven days from today (when a slot is still open) or tomorrow."""
    today = query.now.astimezone(schedule_zone()).date()
    start = today if slots_on(query, today) else today + timedelta(days=1)
    days = [start + timedelta(days=offset) for offset in range(PICKER_DAYS)]
    best = {day: _best_score(query, day) for day in days}
    starred = _starred(best)
    return tuple(DayOption(day=day, starred=day in starred) for day in days)


def best_slot(query: RecommendQuery) -> ScoredSlot:
    """The best slot of the picker's seven days; the earliest wins a tie."""
    slots = [slot for day in picker_days(query) for slot in slots_on(query, day.day)]
    return min(slots, key=lambda slot: (-slot.score, slot.at))


def reason_text(slot: ScoredSlot) -> str:
    """The owner-facing reason, e.g. ``⭐ seus seguidores mais online``."""
    texts = {
        REASON_AUDIENCE: TEXT_REASON_AUDIENCE,
        REASON_PERFORMANCE: TEXT_REASON_PERFORMANCE.format(posts=slot.posts),
        REASON_POV_PLAN: TEXT_REASON_POV_PLAN,
        REASON_DEFAULT_SLOT: TEXT_REASON_DEFAULT_SLOT,
    }
    return texts.get(slot.reason, TEXT_REASON_ALTERNATIVE)


def _best_score(query: RecommendQuery, day: date) -> float:
    slots = slots_on(query, day)
    return slots[0].score if slots else 0.0


def _starred(best: Mapping[date, float]) -> set[date]:
    """Days near the top score, only when the days differ at all."""
    top = max(best.values())
    if top <= min(best.values()):
        return set()
    ranked = sorted(best, key=lambda day: (-best[day], day))
    near = [day for day in ranked if best[day] >= STARRED_DAY_SHARE * top]
    return set(near[:MAX_STARRED_DAYS])


def _rank_key(slot: ScoredSlot) -> tuple[float, int, datetime]:
    hour = slot.at.astimezone(schedule_zone()).hour
    distance = min(abs(hour - _hour(default)) for default in SCHEDULE_SLOTS)
    return (-slot.score, distance, slot.at)


def _hour(slot: str) -> int:
    return int(slot.split(TIME_SEPARATOR)[0])


def _clock(slot: str) -> time:
    hour, minute = slot.split(TIME_SEPARATOR)
    return time(int(hour), int(minute))


_DEFAULT_TIMES = frozenset(_clock(slot) for slot in SCHEDULE_SLOTS)


class _Scorer:
    """The normalised signals of one query."""

    def __init__(self, query: RecommendQuery) -> None:
        self._query = query
        self._buckets = _buckets(query.signals.posts)
        means = [sum(rates) / len(rates) for rates in self._buckets.values()]
        self._best_rate = max(means, default=0.0)

    def parts(self, at: datetime) -> _Parts:
        local = at.astimezone(schedule_zone())
        prior, reason = _prior(local, pov=self._query.pov)
        rates = self._buckets.get((local.weekday(), local.hour), [])
        return _Parts(
            prior=prior,
            audience=_audience(self._query.signals.audience, at.astimezone(UTC).hour),
            performance=self._performance(rates),
            posts=len(rates),
            prior_reason=reason,
        )

    def _performance(self, rates: list[float]) -> float:
        if not rates or self._best_rate <= 0:
            return 0.0
        shrink = len(rates) / (len(rates) + SHRINKAGE_POSTS)
        return shrink * (sum(rates) / len(rates)) / self._best_rate


def _prior(local: datetime, *, pov: bool) -> tuple[float, str]:
    clock = local.time().replace(second=0, microsecond=0)
    if pov and local.weekday() in POV_SLOT_WEEKDAYS and clock == POV_SLOT_TIME:
        return PRIOR_PLAN, REASON_POV_PLAN
    if clock not in _DEFAULT_TIMES:
        return 0.0, REASON_DEFAULT_SLOT
    return (PRIOR_SECONDARY if pov else PRIOR_PLAN), REASON_DEFAULT_SLOT


def _audience(counts: Mapping[int, int], utc_hour: int) -> float:
    """Min-max over the hours Graph returned; 0 when they do not differ."""
    if not counts:
        return 0.0
    low, high = min(counts.values()), max(counts.values())
    if high <= low:
        return 0.0
    return (counts.get(utc_hour, low) - low) / (high - low)


def _buckets(posts: tuple[PostEngagement, ...]) -> dict[_Bucket, list[float]]:
    buckets: dict[_Bucket, list[float]] = defaultdict(list)
    for post in posts:
        local = post.published_at.astimezone(schedule_zone())
        buckets[local.weekday(), local.hour].append(post.rate)
    return dict(buckets)


__all__ = [
    "DayOption",
    "PostEngagement",
    "RecommendQuery",
    "ScheduleSignals",
    "ScoredSlot",
    "best_slot",
    "engagement_rate",
    "picker_days",
    "reason_text",
    "score_slot",
    "slots_on",
    "top_times",
]
