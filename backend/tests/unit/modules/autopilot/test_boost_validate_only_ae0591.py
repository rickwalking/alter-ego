"""The validate-only check posts the real bodies with validate_only and creates nothing.

Gherkin: tests/features/boost_meta_payload_ae0591.feature
"""

from __future__ import annotations

import argparse
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr

from rag_backend.modules.autopilot.boost_constants import GRAPH_CAMPAIGNS
from rag_backend.modules.autopilot.domain.boost import BoostAudience, BoostRequest
from rag_backend.modules.autopilot.domain.boost_policy import BoostLimits
from rag_backend.modules.autopilot.infrastructure.boost_validate_only import (
    OUTCOME_FAILED,
    OUTCOME_NEEDS_PARENT,
    OUTCOME_OK,
    CallOutcome,
    CheckInput,
    ParentIds,
    UnsafePostError,
    ValidateOnlyGraph,
    run_checks,
)
from rag_backend.modules.autopilot.infrastructure.meta_ads_payloads import (
    campaign_payload,
)
from rag_backend.modules.autopilot.infrastructure.meta_graph import GraphCall
from rag_backend.scripts import boost_validate_only as entry
from rag_backend.scripts import boost_validate_only_cli as cli
from tests.unit.modules.autopilot.meta_ads_fakes import (
    MEDIA,
    NOW,
    REQUEST_ID,
    TOKEN,
    Graph,
    config,
    limits,
    meta_error,
    request,
)

_PARENTS = ParentIds(campaign_id="c-1", adset_id="s-1", creative_id="k-1")


async def _run(
    graph: Graph, parents: ParentIds, boost: BoostRequest | None = None
) -> list[CallOutcome]:
    check = CheckInput(request=boost or request(), parents=parents, now=NOW)
    async with graph.client() as client:
        return await run_checks(check, config(), client)


def _posts(graph: Graph) -> list[dict[str, str]]:
    return [item.fields for item in graph.sent if item.method == "POST"]


@pytest.mark.asyncio
async def test_validate_only_check_sends_only_validate_only_posts() -> None:
    # Scenario: The validate-only check sends only validate_only POSTs
    graph = Graph()
    outcomes = await _run(graph, ParentIds())
    assert [(o.call, o.outcome) for o in outcomes] == [
        ("page", OUTCOME_OK),
        ("caps", OUTCOME_OK),
        ("preflight_media", OUTCOME_OK),
        ("preflight_account", OUTCOME_OK),
        ("min_budgets", OUTCOME_OK),
        ("campaign", OUTCOME_OK),
        ("creative", OUTCOME_OK),
        ("adset", OUTCOME_NEEDS_PARENT),
        ("ad", OUTCOME_NEEDS_PARENT),
    ]
    assert [item.call for item in graph.sent if item.method == "POST"] == [
        "campaign",
        "creative",
    ]
    assert all(
        body["execution_options"] == '["validate_only"]' for body in _posts(graph)
    )
    adset = outcomes[7].payload
    assert adset["access_token"] == "[redacted]"
    assert adset["campaign_id"] == "<campaign_id>"
    assert json.loads(adset["targeting"])["geo_locations"] == {"countries": ["BR"]}
    assert "execution_options" not in adset
    assert outcomes[8].payload["adset_id"] == "<adset_id>"
    assert TOKEN not in json.dumps([o.payload for o in outcomes])


@pytest.mark.asyncio
async def test_with_parent_ids_adset_and_ad_are_validated_too() -> None:
    # Scenario: With parent ids the ad set and the ad are validated too
    graph = Graph()
    outcomes = await _run(graph, _PARENTS)
    assert all(o.outcome == OUTCOME_OK for o in outcomes)
    posts = _posts(graph)
    assert len(posts) == 4
    assert all(body["execution_options"] == '["validate_only"]' for body in posts)
    assert graph.body("adset")["campaign_id"] == "c-1"
    assert graph.body("ad")["adset_id"] == "s-1"
    assert json.loads(graph.body("ad")["creative"]) == {"creative_id": "k-1"}


@pytest.mark.asyncio
@pytest.mark.parametrize("execution", [None, '["include_recommendations"]'])
async def test_post_without_validate_only_is_refused_before_it_is_sent(
    execution: str | None,
) -> None:
    # Scenario: A POST without validate_only is refused before it is sent
    graph = Graph()
    params = campaign_payload(request())
    if execution is not None:
        params["execution_options"] = execution
    unsafe = GraphCall(call="campaign", path=GRAPH_CAMPAIGNS, params=params)
    with pytest.raises(UnsafePostError):
        async with graph.client() as client:
            await ValidateOnlyGraph(config(), client).post(unsafe)
    assert graph.sent == []


@pytest.mark.asyncio
async def test_validate_only_check_reports_meta_error_fields_per_call() -> None:
    # Scenario: The validate-only check reports Meta's error fields per call
    graph = Graph(
        fail={
            "creative": meta_error(100, 1885183),
            "preflight_media": meta_error(100, 33),
        }
    )
    outcomes = {o.call: o for o in await _run(graph, ParentIds())}
    creative = outcomes["creative"]
    assert (creative.outcome, creative.error_code) == (
        OUTCOME_FAILED,
        "meta_app_dev_mode",
    )
    assert (
        creative.detail["error_user_msg"] == "It must be in public to create this ad."
    )
    assert outcomes["preflight_media"].error_code == "meta_media_unreadable"
    assert outcomes["campaign"].outcome == OUTCOME_OK
    lines = [cli.render(o) for o in outcomes.values()]
    assert all(TOKEN not in line for line in lines)
    assert json.loads(cli.render(creative))["meta"]["call"] == "creative"


@pytest.mark.asyncio
async def test_transport_failure_is_reported_by_its_type_only() -> None:
    # Scenario: The validate-only check reports Meta's error fields per call
    def refuse(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {req.url}")

    check = CheckInput(request=request(), parents=ParentIds(), now=NOW)
    async with httpx.AsyncClient(transport=httpx.MockTransport(refuse)) as client:
        outcomes = await run_checks(check, config(), client)
    assert outcomes[2] == CallOutcome(
        call="preflight_media", outcome=OUTCOME_FAILED, error_code="ConnectError"
    )
    assert all(TOKEN not in cli.render(o) for o in outcomes)


@pytest.mark.asyncio
async def test_validate_only_check_reports_an_audience_outside_the_caps() -> None:
    # Scenario: The validate-only check reports an audience outside the caps
    graph = Graph()
    boost = request(
        audience=BoostAudience(countries=("BR", "US"), age_min=18, age_max=65)
    )
    outcomes = {o.call: o for o in await _run(graph, _PARENTS, boost)}
    assert (outcomes["adset"].outcome, outcomes["adset"].error_code) == (
        OUTCOME_FAILED,
        "country_not_allowed",
    )
    assert outcomes["ad"].outcome == OUTCOME_OK
    assert "adset" not in graph.calls()


class _Store:
    def __init__(self, found: BoostRequest | None) -> None:
        self._found = found

    async def committed_cents(self, since: datetime) -> int:
        del since
        return 0

    async def get(self, request_id: UUID) -> BoostRequest | None:
        assert request_id == REQUEST_ID
        return self._found


@asynccontextmanager
async def _session(engine: object) -> AsyncIterator[object]:
    del engine
    yield object()


async def _own_engine(runner: Callable[[object], Awaitable[int]]) -> int:
    return await runner(object())


def _captured_cli(argv: list[str]) -> tuple[cli.GuardedCli, argparse.Namespace]:
    """The parsed CLI from ``main``, without letting it start its own event loop."""
    seen: list[cli.GuardedCli] = []
    with patch.object(
        cli, "run_guarded_cli", lambda guarded, args: seen.append(guarded) or 0
    ):
        cli.main(argv)
    return seen[0], seen[0].parser.parse_args(argv)


@dataclass(frozen=True, kw_only=True)
class _Env:
    found: BoostRequest | None
    token: str = TOKEN
    caps: BoostLimits = field(default_factory=limits)


async def _main(graph: Graph, env: _Env) -> int:
    guarded, args = _captured_cli([str(REQUEST_ID), "--campaign-id", "c-1"])
    assert guarded.validate(args) is None
    real_client = httpx.AsyncClient
    settings = SimpleNamespace(meta_ads_access_token=SecretStr(env.token))
    with (
        patch.object(cli, "AsyncSession", _session),
        patch.object(cli, "SqlBoostStore", lambda session: _Store(env.found)),
        patch.object(cli, "limits_from", lambda s: env.caps),
        patch.object(cli, "get_settings", lambda: settings),
        patch.object(cli, "ads_config", lambda s, t: config()),
        patch.object(cli, "run_on_own_engine", _own_engine),
        patch.object(
            cli.httpx,
            "AsyncClient",
            lambda **kw: real_client(transport=httpx.MockTransport(graph.handle)),
        ),
    ):
        return await guarded.run(args)


@pytest.mark.asyncio
async def test_validate_only_command_prints_one_line_per_call(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Scenario: The validate-only command loads the request and prints one line per call
    graph = Graph()
    assert await _main(graph, _Env(found=request())) == cli.EXIT_OK
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [line["call"] for line in lines] == [
        "page",
        "caps",
        "preflight_media",
        "preflight_account",
        "min_budgets",
        "campaign",
        "creative",
        "adset",
        "ad",
    ]
    assert lines[-1]["outcome"] == OUTCOME_NEEDS_PARENT
    assert all(
        item.fields.get("execution_options") == '["validate_only"]'
        for item in graph.sent
        if item.method == "POST"
    )
    assert graph.body("preflight_media")["fields"] == "id"
    assert MEDIA in graph.sent[0].url


@pytest.mark.asyncio
async def test_validate_only_command_exits_one_when_a_call_fails(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Scenario: The validate-only command loads the request and prints one line per call
    graph = Graph(fail={"creative": meta_error(100, 1885183)})
    assert await _main(graph, _Env(found=request())) == cli.EXIT_FAILED
    assert TOKEN not in capsys.readouterr().out


@pytest.mark.asyncio
async def test_validate_only_command_refuses_without_request_token_or_uuid(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Scenario: The validate-only command refuses a missing request, a missing token or a bad id
    graph = Graph()
    assert await _main(graph, _Env(found=None)) == cli.EXIT_FAILED
    assert await _main(graph, _Env(found=request(), token="  ")) == cli.EXIT_FAILED
    guarded, args = _captured_cli(["not-a-uuid"])
    assert guarded.validate(args) == "request_id must be a UUID"
    assert graph.sent == []
    err = capsys.readouterr().err
    assert "boost request not found" in err


def test_entry_point_loads_the_command_and_refuses_a_bad_id(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Scenario: The validate-only command refuses a missing request, a missing token or a bad id
    assert entry.main(["not-a-uuid"]) == cli.EXIT_USAGE
    assert "request_id must be a UUID" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_validate_only_command_fails_on_caps_the_worker_would_refuse(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Scenario: The validate-only check fails without a Page and on caps the worker would refuse
    graph = Graph()
    env = _Env(found=request(), caps=limits(max_daily_cents=1000))
    assert await _main(graph, env) == cli.EXIT_FAILED
    lines = {
        json.loads(line)["call"]: json.loads(line)
        for line in capsys.readouterr().out.splitlines()
    }
    assert lines["caps"]["outcome"] == OUTCOME_FAILED
    assert lines["caps"]["error_code"] == "daily_budget_over_cap"
