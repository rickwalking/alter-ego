"""The caps in force bind at launch, on the worker and inside the Meta bodies.

Gherkin: tests/features/boost_meta_payload_ae0591.feature
"""

from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest
from pydantic import SecretStr

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.autopilot.application.boost_requests import BoostDeps
from rag_backend.modules.autopilot.application.boost_tick import (
    BoostTick,
    BoostTickDeps,
)
from rag_backend.modules.autopilot.boost_constants import (
    STATUS_ACTIVE,
    STATUS_APPROVED,
    STATUS_FAILED,
)
from rag_backend.modules.autopilot.domain.boost import BoostAudience
from rag_backend.modules.autopilot.domain.boost_policy import BoostLimits
from rag_backend.modules.autopilot.infrastructure.boost_validate_only import (
    OUTCOME_FAILED,
    CallOutcome,
    CheckInput,
    ParentIds,
    run_checks,
)
from rag_backend.modules.autopilot.infrastructure.meta_ads_errors import AdsCallError
from rag_backend.modules.autopilot.infrastructure.meta_graph import (
    AdsCaps,
    AdsConfig,
    ads_config,
)
from tests.unit.modules.autopilot.meta_ads_fakes import (
    NOW,
    Clock,
    Graph,
    Msg,
    Store,
    config,
    gateway,
    limits,
    request,
)


async def _tick(store: Store, caps: BoostLimits, graph: Graph) -> int:
    deps = BoostDeps(store=store, messenger=Msg(), clock=Clock(), owner_chat_id="1")
    tick = BoostTick(BoostTickDeps(boosts=deps, limits=caps, ads=gateway(graph)))
    return await tick.run()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("caps", "code"),
    [
        (limits(max_daily_cents=1000), "daily_budget_over_cap"),
        (limits(min_daily_cents=2500), "daily_budget_under_floor"),
        (limits(max_days=2), "days_over_cap"),
        (limits(max_week_cents=5000), "weekly_cap_exceeded"),
        (
            replace(limits(), allowed_countries=frozenset({"PT"})),
            "country_not_allowed",
        ),
    ],
)
async def test_worker_fails_a_boost_the_current_caps_no_longer_allow(
    caps: BoostLimits, code: str
) -> None:
    # Scenario: The worker fails an approved boost that the current caps no longer allow
    store = Store(row=request(days=3))
    graph = Graph()
    assert await _tick(store, caps, graph) == 1
    assert store.row.status == STATUS_FAILED
    assert store.row.error_code == code
    assert [save.previous for save in store.saves] == [STATUS_APPROVED]
    assert store.commits == 1
    assert graph.sent == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("committed", "status"), [(10000, STATUS_ACTIVE), (10001, STATUS_FAILED)]
)
async def test_weekly_cap_counts_other_commitments_not_the_request_itself(
    committed: int, status: str
) -> None:
    # Scenario: The weekly cap counts other commitments but not the request itself
    store = Store(row=request(days=3), committed=committed)
    graph = Graph()
    await _tick(store, limits(), graph)
    assert store.row.status == status
    assert bool(graph.sent) is (status == STATUS_ACTIVE)


@pytest.mark.asyncio
async def test_adset_is_built_inside_the_configured_caps() -> None:
    # Scenario: The ad set is built inside the configured caps
    caps = AdsCaps(max_days=2, countries=frozenset({"BR", "PT"}))
    two_countries = BoostAudience(countries=("PT", "BR"), age_min=18, age_max=65)
    graph = Graph()
    await gateway(graph, config(caps=caps)).launch(
        request(audience=two_countries, days=2)
    )
    countries = json.loads(graph.body("adset")["targeting"])["geo_locations"]
    assert countries == {"countries": ["BR", "PT"]}
    with pytest.raises(AdsCallError) as caught:
        await gateway(Graph(), config(caps=caps)).launch(request(days=3))
    assert caught.value.code == "days_over_cap"


def test_ads_config_takes_the_caps_from_settings() -> None:
    # Scenario: The ad set is built inside the configured caps
    settings = Settings.model_construct(
        meta_ads_app_secret=SecretStr(" s "),
        boost_max_days=3,
        boost_allowed_countries="BR, PT,",
    )
    built = ads_config(settings, "tok")
    assert built.caps == AdsCaps(max_days=3, countries=frozenset({"BR", "PT"}))
    assert built.app_secret == "s"


@pytest.mark.asyncio
async def test_launch_bodies_never_carry_execution_options() -> None:
    # Scenario: The launch bodies never carry execution_options
    graph = Graph()
    await gateway(graph).launch(request())
    posts = [item for item in graph.sent if item.method == "POST"]
    assert [item.call for item in posts] == [
        "campaign",
        "adset",
        "creative",
        "ad",
        "activate",
        "activate",
        "activate",
    ]
    assert all("execution_options" not in item.fields for item in posts)
    assert all("execution_options" not in item.url for item in graph.sent)


async def _checks(graph: Graph, ads: AdsConfig) -> dict[str, CallOutcome]:
    check = CheckInput(request=request(), parents=ParentIds(), now=NOW)
    async with graph.client() as client:
        return {o.call: o for o in await run_checks(check, ads, client)}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("call", "body", "code"),
    [
        ("preflight_media", {}, "media_not_visible_to_ads"),
        ("preflight_account", {"account_status": 2}, "ad_account_inactive"),
        ("min_budgets", {"min_daily_budget_high_freq": 5000}, "below_meta_minimum"),
    ],
)
async def test_validate_only_fails_where_the_launch_preflight_would_fail(
    call: str, body: dict[str, object], code: str
) -> None:
    # Scenario: The validate-only check fails where the launch preflight would fail
    graph = Graph(fail={call: httpx.Response(200, json=body)})
    outcome = (await _checks(graph, config()))[call]
    assert (outcome.outcome, outcome.error_code) == (OUTCOME_FAILED, code)
    assert outcome.detail == {"call": call}
    with pytest.raises(AdsCallError) as caught:
        await gateway(Graph(fail={call: httpx.Response(200, json=body)})).launch(
            request()
        )
    assert caught.value.code == code


@pytest.mark.asyncio
async def test_validate_only_fails_without_a_page() -> None:
    # Scenario: The validate-only check fails without a Page and on caps the worker would refuse
    outcomes = await _checks(Graph(), config(page_id=" "))
    assert (outcomes["page"].outcome, outcomes["page"].error_code) == (
        OUTCOME_FAILED,
        "meta_page_missing",
    )
    assert outcomes["campaign"].outcome != OUTCOME_FAILED


@pytest.mark.asyncio
async def test_malformed_graph_url_is_reported_by_its_type_only() -> None:
    # Scenario: A malformed Graph URL is reported by its type only
    outcomes = await _checks(
        Graph(), config(graph_base="https://graph.example:abc/v23.0")
    )
    assert outcomes["preflight_media"] == CallOutcome(
        call="preflight_media", outcome=OUTCOME_FAILED, error_code="InvalidURL"
    )
    assert outcomes["campaign"].error_code == "InvalidURL"
