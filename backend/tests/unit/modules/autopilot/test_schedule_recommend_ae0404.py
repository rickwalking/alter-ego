"""Recommended publish slots, pure rules.

Gherkin: tests/features/telegram_schedule_picker_ae0404.feature

_NOW is Friday 2026-10-16 10:00 in São Paulo, the time of the owner's report.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.domain.recommend import (
    PostEngagement,
    RecommendQuery,
    ScheduleSignals,
    ScoredSlot,
    best_slot,
    engagement_rate,
    picker_days,
    reason_text,
    score_slot,
    slots_on,
    top_times,
)

_SP = ZoneInfo("America/Sao_Paulo")
_NOW = datetime(2026, 10, 16, 10, 0, tzinfo=_SP).astimezone(UTC)


def _local(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=_SP).astimezone(UTC)


def _query(
    signals: ScheduleSignals | None = None, *, pov: bool = False, now: datetime = _NOW
) -> RecommendQuery:
    return RecommendQuery(now=now, pov=pov, signals=signals or ScheduleSignals())


def _hours(slots: tuple[ScoredSlot, ...]) -> list[int]:
    return [slot.at.astimezone(_SP).hour for slot in slots]


def _peak_at_20() -> ScheduleSignals:
    """Followers online peak at 20:00 São Paulo (23:00 UTC).

    Hour 22 UTC is 19:00 in São Paulo.
    """
    audience = dict.fromkeys(range(24), 100)
    audience[23] = 900
    audience[22] = 500
    return ScheduleSignals(audience=audience)


def _posts(count: int, rate: float = 0.5) -> ScheduleSignals:
    """``count`` posts on Wednesdays at 15:00 São Paulo, plus one weak post."""
    strong = tuple(
        PostEngagement(published_at=_local(14, 15, minute % 50), rate=rate)
        for minute in range(count)
    )
    weak = PostEngagement(published_at=_local(13, 9), rate=0.01)
    return ScheduleSignals(posts=(*strong, weak))


@pytest.mark.unit
class TestNoInsights:
    # Scenario: With no insights the POV prior wins
    def test_pov_prior_wins(self) -> None:
        best = best_slot(_query(pov=True))
        assert best.at == _local(20, 12)
        assert reason_text(best) == "padrão do plano POV"

    # Scenario: Without insights a Radar run keeps the default slots
    def test_radar_keeps_the_default_slots(self) -> None:
        best = best_slot(_query())
        assert best.at == _local(16, 12)
        assert reason_text(best) == "horário padrão"

    def test_radar_top_times_are_the_default_slots_then_a_neighbour(self) -> None:
        slots = top_times(_query(), date(2026, 10, 17))
        assert _hours(slots) == [12, 18, 21, 11]
        assert reason_text(slots[-1]) == "horário alternativo"

    def test_pov_day_keeps_default_slots_as_a_secondary_prior(self) -> None:
        slots = top_times(_query(pov=True), date(2026, 10, 20))
        assert _hours(slots)[:3] == [12, 18, 21]
        assert slots[0].score > slots[1].score


@pytest.mark.unit
class TestAudience:
    # Scenario: With online_followers the peak hours rank first
    def test_peak_hour_ranks_first_on_every_day(self) -> None:
        query = _query(_peak_at_20())
        for day in picker_days(query):
            first = top_times(query, day.day)[0]
            assert first.at.astimezone(_SP).hour == 20
            assert reason_text(first) == "⭐ seus seguidores mais online"

    def test_auto_slot_follows_the_audience(self) -> None:
        assert best_slot(_query(_peak_at_20())).at == _local(16, 20)

    def test_flat_audience_is_no_signal(self) -> None:
        flat = ScheduleSignals(audience=dict.fromkeys(range(24), 50))
        assert best_slot(_query(flat)).at == _local(16, 12)

    def test_missing_hours_count_as_the_minimum(self) -> None:
        sparse = ScheduleSignals(audience={23: 10, 0: 5})
        slot = score_slot(_query(sparse), _local(16, 12))
        assert slot.reason == "default_slot"


@pytest.mark.unit
class TestPerformance:
    # Scenario: Post performance shifts the ranking with shrinkage
    def test_three_posts_barely_move_it(self) -> None:
        slots = top_times(_query(_posts(3)), date(2026, 10, 21))
        assert _hours(slots) == [12, 18, 21, 15]
        assert slots[-1].reason == "performance"
        assert reason_text(slots[-1]) == "⭐ melhor engajamento (3 posts)"

    def test_thirty_posts_rank_first(self) -> None:
        query = _query(_posts(30))
        first = top_times(query, date(2026, 10, 21))[0]
        assert first.at == _local(21, 15)
        assert reason_text(first) == "⭐ melhor engajamento (30 posts)"
        assert best_slot(query).at == _local(21, 15)

    def test_more_posts_weigh_more(self) -> None:
        few = score_slot(_query(_posts(3)), _local(21, 15)).score
        many = score_slot(_query(_posts(30)), _local(21, 15)).score
        assert 0 < few < many

    def test_other_weekdays_are_untouched(self) -> None:
        slot = score_slot(_query(_posts(30)), _local(22, 15))
        assert slot.score == 0
        assert slot.reason == "alternative"

    def test_zero_engagement_is_no_signal(self) -> None:
        slot = score_slot(_query(_posts(30, rate=0.0)), _local(21, 15))
        assert slot.score == 0


@pytest.mark.unit
class TestPickerDays:
    # Scenario: The day keyboard lists the next 7 days and stars the best ones
    def test_starts_today_while_a_slot_is_open(self) -> None:
        days = picker_days(_query())
        assert days[0].day == date(2026, 10, 16)
        assert len(days) == 7

    # Scenario: The day keyboard starts tomorrow late in the day
    def test_starts_tomorrow_late_in_the_day(self) -> None:
        late = _query(now=_local(16, 22))
        assert picker_days(late)[0].day == date(2026, 10, 17)

    def test_pov_days_are_starred(self) -> None:
        starred = [d.day for d in picker_days(_query(pov=True)) if d.starred]
        assert starred == [date(2026, 10, 20), date(2026, 10, 22)]

    def test_equal_days_have_no_star(self) -> None:
        assert not any(d.starred for d in picker_days(_query()))

    def test_open_slots_respect_the_lead(self) -> None:
        slots = slots_on(_query(now=_local(16, 11, 50)), date(2026, 10, 16))
        assert min(slot.at for slot in slots) == _local(16, 13)


@pytest.mark.unit
class TestEngagementRate:
    def test_rate_over_reach(self) -> None:
        metrics = InsightMetrics(reach=200, saved=10, shares=5, total_interactions=25)
        assert engagement_rate(metrics) == 0.2

    def test_missing_metrics_count_as_zero(self) -> None:
        assert engagement_rate(InsightMetrics(reach=10, saved=1)) == 0.1

    @pytest.mark.parametrize("reach", [None, 0])
    def test_no_reach_is_none(self, reach: int | None) -> None:
        assert engagement_rate(InsightMetrics(reach=reach, saved=3)) is None
