"""The ad set carries the capped audience and run window; caps are checked before HTTP.

Gherkin: tests/features/boost_meta_payload_ae0591.feature
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import timedelta

import pytest

from rag_backend.modules.autopilot.boost_constants import (
    ERR_AUDIENCE,
    ERR_COUNTRY,
    ERR_DAYS,
)
from rag_backend.modules.autopilot.domain.boost import BoostAudience
from rag_backend.modules.autopilot.infrastructure.meta_ads_errors import AdsCallError
from rag_backend.modules.autopilot.meta_ads_constants import ERR_SCHEDULE
from tests.unit.modules.autopilot.meta_ads_fakes import (
    IG_USER,
    MEDIA,
    NOW,
    PAGE,
    Graph,
    gateway,
    request,
)


def _stamp(days: float) -> str:
    return str(int((NOW + timedelta(days=days)).timestamp()))


@pytest.mark.asyncio
async def test_adset_carries_capped_brazil_audience_and_run_window() -> None:
    # Scenario: The ad set carries the capped Brazil audience and the run window
    graph = Graph()
    await gateway(graph).launch(request(days=3))
    adset = graph.body("adset")
    assert json.loads(adset["targeting"]) == {
        "geo_locations": {"countries": ["BR"]},
        "age_min": 18,
        "age_max": 65,
        "publisher_platforms": ["instagram"],
        "instagram_positions": ["stream"],
        "targeting_automation": {"advantage_audience": 0},
    }
    assert adset["start_time"] == _stamp(0)
    assert adset["end_time"] == _stamp(3)
    assert adset["destination_type"] == "ON_POST"
    assert adset["optimization_goal"] == "POST_ENGAGEMENT"
    assert adset["bid_strategy"] == "LOWEST_COST_WITHOUT_CAP"
    assert adset["daily_budget"] == "2000"
    assert adset["status"] == "PAUSED"
    assert adset["campaign_id"].startswith("id-campaign-")


@pytest.mark.asyncio
async def test_future_start_is_kept_and_end_is_start_plus_days() -> None:
    # Scenario: A requested future start is kept and the end is the start plus the days
    graph = Graph()
    tomorrow = NOW + timedelta(days=1)
    launched = await gateway(graph).launch(request(days=2, starts_at=tomorrow))
    adset = graph.body("adset")
    assert adset["start_time"] == _stamp(1)
    assert adset["end_time"] == _stamp(3)
    assert launched.starts_at == tomorrow
    assert launched.ends_at == tomorrow + timedelta(days=2)


@pytest.mark.asyncio
async def test_past_start_runs_from_now_and_existing_adset_keeps_its_window() -> None:
    # Scenario: A requested future start is kept and the end is the start plus the days
    graph = Graph()
    launched = await gateway(graph).launch(
        request(days=1, starts_at=NOW - timedelta(days=2))
    )
    assert launched.starts_at == NOW
    assert launched.ends_at == NOW + timedelta(days=1)
    resumed = replace(request(), meta_adset_id="adset-1", starts_at=None, ends_at=None)
    again = await gateway(Graph()).launch(resumed)
    assert again.starts_at is None
    assert again.ends_at is None


@pytest.mark.asyncio
async def test_creative_and_ad_use_existing_instagram_post_form() -> None:
    # Scenario: The creative and the ad use the existing Instagram post form
    graph = Graph()
    await gateway(graph).launch(request())
    creative = graph.body("creative")
    assert creative["object_id"] == PAGE
    assert creative["instagram_user_id"] == IG_USER
    assert creative["source_instagram_media_id"] == MEDIA
    ad = graph.body("ad")
    assert ad["adset_id"].startswith("id-adset-")
    assert json.loads(ad["creative"]) == {"creative_id": creative_id(graph)}
    assert ad["status"] == "PAUSED"
    campaign = graph.body("campaign")
    assert campaign["objective"] == "OUTCOME_ENGAGEMENT"
    assert campaign["is_adset_budget_sharing_enabled"] == "false"


def creative_id(graph: Graph) -> str:
    """The id the fake gave the creative (its position in the sent list)."""
    index = graph.calls().index("creative") + 1
    return f"id-creative-{index}"


async def _refused(
    audience: BoostAudience | None = None, days: int = 3
) -> tuple[AdsCallError, Graph]:
    graph = Graph()
    with pytest.raises(AdsCallError) as caught:
        await gateway(graph).launch(request(audience=audience, days=days))
    return caught.value, graph


@pytest.mark.asyncio
@pytest.mark.parametrize("countries", [("BR", "US"), ("US",), ()])
async def test_audience_outside_brazil_is_refused_before_any_meta_call(
    countries: tuple[str, ...],
) -> None:
    # Scenario: An audience outside Brazil is refused before any Meta call
    error, graph = await _refused(
        BoostAudience(countries=countries, age_min=18, age_max=65)
    )
    assert error.code == ERR_COUNTRY
    assert error.permanent is True
    assert graph.sent == []


@pytest.mark.asyncio
@pytest.mark.parametrize(("age_min", "age_max"), [(16, 65), (18, 70), (40, 30)])
async def test_age_band_outside_caps_is_refused_before_any_meta_call(
    age_min: int, age_max: int
) -> None:
    # Scenario: An age band outside 18 to 65 is refused before any Meta call
    audience = BoostAudience(countries=("BR",), age_min=age_min, age_max=age_max)
    error, graph = await _refused(audience)
    assert error.code == ERR_AUDIENCE
    assert error.permanent is True
    assert graph.sent == []


@pytest.mark.asyncio
async def test_run_longer_than_the_cap_is_refused_before_any_meta_call() -> None:
    # Scenario: A run longer than the 7-day cap is refused before any Meta call
    error, graph = await _refused(days=8)
    assert error.code == ERR_DAYS
    assert error.permanent is True
    assert graph.sent == []


@pytest.mark.asyncio
async def test_seven_day_run_ends_exactly_at_the_cap() -> None:
    # Scenario: A run longer than the 7-day cap is refused before any Meta call
    graph = Graph()
    await gateway(graph).launch(request(days=7))
    assert graph.body("adset")["end_time"] == _stamp(7)


@pytest.mark.asyncio
async def test_zero_day_run_is_refused_before_any_meta_call() -> None:
    # Scenario: A run of zero days is refused before any Meta call
    error, graph = await _refused(days=0)
    assert error.code == ERR_SCHEDULE
    assert error.permanent is True
    assert graph.sent == []
