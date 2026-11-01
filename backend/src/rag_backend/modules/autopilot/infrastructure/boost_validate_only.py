"""Check one boost's real launch bodies with Meta's ``validate_only``. Creates nothing.

Every POST goes through ``ValidateOnlyGraph``, which refuses to send a body that
does not carry ``execution_options=["validate_only"]``. The preflight reads are plain
GETs. The ad set and the ad need real parent ids; without them their exact body is
reported (no token) instead of being sent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import httpx

from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN
from rag_backend.modules.autopilot.boost_constants import (
    GRAPH_ADS,
    GRAPH_ADSETS,
    GRAPH_CAMPAIGNS,
    GRAPH_CREATIVES,
)
from rag_backend.modules.autopilot.domain.boost import BoostRequest
from rag_backend.modules.autopilot.infrastructure.meta_ads_errors import AdsCallError
from rag_backend.modules.autopilot.infrastructure.meta_ads_gateway import (
    account_check,
    budget_floor_check,
    media_check,
)
from rag_backend.modules.autopilot.infrastructure.meta_ads_payloads import (
    ad_payload,
    adset_payload,
    adset_window,
    campaign_payload,
    creative_payload,
)
from rag_backend.modules.autopilot.infrastructure.meta_graph import (
    AdsConfig,
    GraphCall,
    GraphCaller,
)
from rag_backend.modules.autopilot.meta_ads_constants import (
    CALL_AD,
    CALL_ADSET,
    CALL_CAMPAIGN,
    CALL_CREATIVE,
    EXECUTION_OPTIONS,
    REDACTED,
    VALIDATE_ONLY_VALUE,
)

OUTCOME_OK = "ok"
OUTCOME_FAILED = "failed"
OUTCOME_NEEDS_PARENT = "needs_parent_id"
PARENT_PLACEHOLDER = "<{name}>"


class UnsafePostError(RuntimeError):
    """A POST without ``validate_only`` reached the checker. Nothing was sent."""


@dataclass(frozen=True, kw_only=True)
class CallOutcome:
    """One call's result: ok, Meta's error fields, or the body that was not sent."""

    call: str
    outcome: str
    error_code: str = ""
    detail: dict[str, str] = field(default_factory=dict)
    payload: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class ParentIds:
    """Existing Meta objects to validate the ad set and the ad against."""

    campaign_id: str | None = None
    adset_id: str | None = None
    creative_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class CheckInput:
    """The stored request, the parent ids and the time the ad set would start."""

    request: BoostRequest
    parents: ParentIds
    now: datetime


class ValidateOnlyGraph:
    """Signed GETs, and POSTs only when they carry ``validate_only``."""

    def __init__(self, config: AdsConfig, client: httpx.AsyncClient) -> None:
        self._graph = GraphCaller(config, client)

    async def get(self, call: GraphCall) -> dict[str, object]:
        """A read. Reads never create anything."""
        return await self._graph.get(call)

    async def post(self, call: GraphCall) -> dict[str, object]:
        """Refuse before sending unless the body asks Meta to only validate."""
        if call.params.get(EXECUTION_OPTIONS) != VALIDATE_ONLY_VALUE:
            raise UnsafePostError(call.call)
        return await self._graph.post(call)


def validate_only(call: GraphCall) -> GraphCall:
    """The same call with ``execution_options=["validate_only"]``."""
    params = dict(call.params)
    params[EXECUTION_OPTIONS] = VALIDATE_ONLY_VALUE
    return GraphCall(call=call.call, path=call.path, params=params)


def shown(payload: dict[str, str]) -> dict[str, str]:
    """A body for printing, with the token slot shown as redacted."""
    printable = dict(payload)
    printable[COOKIE_ACCESS_TOKEN] = REDACTED
    return printable


async def _attempt(
    graph: ValidateOnlyGraph, call: GraphCall, *, write: bool
) -> CallOutcome:
    try:
        await (graph.post(call) if write else graph.get(call))
    except AdsCallError as exc:
        return CallOutcome(
            call=call.call,
            outcome=OUTCOME_FAILED,
            error_code=exc.code,
            detail=exc.detail,
        )
    except httpx.HTTPError as exc:
        return CallOutcome(
            call=call.call, outcome=OUTCOME_FAILED, error_code=type(exc).__name__
        )
    return CallOutcome(call=call.call, outcome=OUTCOME_OK)


def _held(call: GraphCall) -> CallOutcome:
    return CallOutcome(
        call=call.call, outcome=OUTCOME_NEEDS_PARENT, payload=shown(call.params)
    )


def _placeholder(value: str | None, name: str) -> str:
    return value if value else PARENT_PLACEHOLDER.format(name=name)


Write = tuple[GraphCall, bool]


def _adset(check: CheckInput) -> Write:
    """The ad set body. An audience or run length outside the caps raises here."""
    window = adset_window(check.request, check.now)
    parent = _placeholder(check.parents.campaign_id, "campaign_id")
    payload = adset_payload(check.request, parent, window)
    call = GraphCall(call=CALL_ADSET, path=GRAPH_ADSETS, params=payload)
    return call, bool(check.parents.campaign_id)


def _ad(parents: ParentIds) -> Write:
    adset_id = _placeholder(parents.adset_id, "adset_id")
    creative_id = _placeholder(parents.creative_id, "creative_id")
    payload = ad_payload(adset_id, creative_id)
    call = GraphCall(call=CALL_AD, path=GRAPH_ADS, params=payload)
    return call, bool(parents.adset_id and parents.creative_id)


def _roots(check: CheckInput, config: AdsConfig) -> list[Write]:
    """The campaign and the creative need no parent, so both are always validated."""
    campaign = campaign_payload(check.request)
    creative = creative_payload(check.request, config)
    return [
        (GraphCall(call=CALL_CAMPAIGN, path=GRAPH_CAMPAIGNS, params=campaign), True),
        (GraphCall(call=CALL_CREATIVE, path=GRAPH_CREATIVES, params=creative), True),
    ]


async def _write(graph: ValidateOnlyGraph, write: Write) -> CallOutcome:
    call, ready = write
    if not ready:
        return _held(call)
    return await _attempt(graph, validate_only(call), write=True)


async def _children(check: CheckInput, graph: ValidateOnlyGraph) -> list[CallOutcome]:
    try:
        adset = _adset(check)
    except AdsCallError as exc:
        refused = CallOutcome(
            call=CALL_ADSET, outcome=OUTCOME_FAILED, error_code=exc.code
        )
        return [refused, await _write(graph, _ad(check.parents))]
    return [await _write(graph, adset), await _write(graph, _ad(check.parents))]


async def run_checks(
    check: CheckInput, config: AdsConfig, client: httpx.AsyncClient
) -> list[CallOutcome]:
    """Preflight reads, then every write as ``validate_only`` or as a held body."""
    graph = ValidateOnlyGraph(config, client)
    reads = (media_check(check.request.media_id), account_check(), budget_floor_check())
    outcomes = [await _attempt(graph, call, write=False) for call in reads]
    outcomes += [await _write(graph, write) for write in _roots(check, config)]
    return outcomes + await _children(check, graph)


__all__ = [
    "OUTCOME_FAILED",
    "OUTCOME_NEEDS_PARENT",
    "OUTCOME_OK",
    "CallOutcome",
    "CheckInput",
    "ParentIds",
    "UnsafePostError",
    "ValidateOnlyGraph",
    "run_checks",
    "shown",
    "validate_only",
]
