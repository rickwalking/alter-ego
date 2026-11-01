"""Marketing API failures keep the call name and Meta's error fields, never a secret.

Gherkin: tests/features/boost_meta_payload_ae0591.feature
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

import httpx
import pytest
from structlog.testing import capture_logs

from rag_backend.modules.autopilot.application.boost_requests import BoostDeps
from rag_backend.modules.autopilot.application.boost_tick import (
    BoostTick,
    BoostTickDeps,
)
from rag_backend.modules.autopilot.boost_constants import STATUS_FAILED
from rag_backend.modules.autopilot.domain.boost import (
    BoostListQuery,
    BoostRequest,
    MediaEligibility,
    StatusSave,
)
from rag_backend.modules.autopilot.domain.boost_policy import BoostLimits
from rag_backend.modules.autopilot.domain.ig_media import OpenBoost
from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.infrastructure.meta_ads_errors import (
    AdsCallError,
    CallContext,
    read_body,
)
from tests.unit.modules.autopilot.meta_ads_fakes import (
    APP_SECRET,
    NOW,
    TOKEN,
    Graph,
    gateway,
    meta_error,
    request,
)

_PROOF = hmac.new(APP_SECRET.encode(), TOKEN.encode(), hashlib.sha256).hexdigest()


async def _failed(graph: Graph) -> AdsCallError:
    with pytest.raises(AdsCallError) as caught:
        await gateway(graph).launch(request())
    return caught.value


@pytest.mark.asyncio
async def test_creative_in_dev_mode_fails_with_meta_app_dev_mode() -> None:
    # Scenario: A creative refused for an app in development mode fails with meta_app_dev_mode
    error = await _failed(Graph(fail={"creative": meta_error(100, 1885183)}))
    assert error.code == "meta_app_dev_mode"
    assert error.permanent is True
    assert error.detail == {
        "call": "creative",
        "http_status": "400",
        "code": "100",
        "error_subcode": "1885183",
        "type": "OAuthException",
        "message": "Invalid",
        "error_user_title": "Ads creative post was created by an app that is in development mode",
        "error_user_msg": "It must be in public to create this ad.",
        "fbtrace_id": "AbCdEf123",
    }


@pytest.mark.asyncio
async def test_unreadable_media_preflight_fails_with_meta_media_unreadable() -> None:
    # Scenario: A media preflight the ads token cannot read fails with meta_media_unreadable
    graph = Graph(fail={"preflight_media": meta_error(100, 33)})
    error = await _failed(graph)
    assert error.code == "meta_media_unreadable"
    assert error.permanent is True
    assert error.detail["call"] == "preflight_media"
    assert error.detail["error_subcode"] == "33"
    assert graph.calls() == ["preflight_media"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call",
    [
        "preflight_media",
        "preflight_account",
        "min_budgets",
        "campaign",
        "adset",
        "creative",
        "ad",
        "activate",
    ],
)
async def test_every_failing_call_is_named_with_meta_error_fields(call: str) -> None:
    # Scenario: Every failing call is named with Meta's error fields
    error = await _failed(Graph(fail={call: meta_error(190, 463)}))
    assert error.code == "meta_190"
    assert error.permanent is True
    assert error.detail["call"] == call
    assert error.detail["code"] == "190"
    assert error.detail["error_subcode"] == "463"
    assert error.detail["type"] == "OAuthException"


@pytest.mark.asyncio
async def test_code_100_subcode_33_outside_the_media_call_keeps_meta_100() -> None:
    # Scenario: Every failing call is named with Meta's error fields
    error = await _failed(Graph(fail={"campaign": meta_error(100, 33)}))
    assert error.code == "meta_100"


@pytest.mark.asyncio
async def test_meta_error_details_never_carry_the_token_or_proof() -> None:
    # Scenario: Meta's error details never carry the token or the appsecret proof
    echoed = f"bad access_token={TOKEN}&appsecret_proof={_PROOF} " + "x" * 600
    error = await _failed(Graph(fail={"campaign": meta_error(100, message=echoed)}))
    rendered = json.dumps(error.detail)
    assert TOKEN not in rendered
    assert _PROOF not in rendered
    assert "[redacted]" in error.detail["message"]
    assert len(error.detail["message"]) == 500
    assert "error_subcode" not in error.detail


@pytest.mark.asyncio
async def test_server_error_stays_transient_and_keeps_meta_details() -> None:
    # Scenario: A server error stays transient and keeps Meta's details
    body = {
        "error": {
            "code": 2,
            "type": "OAuthException",
            "message": "Service unavailable",
            "is_transient": True,
        }
    }
    error = await _failed(Graph(fail={"campaign": httpx.Response(500, json=body)}))
    assert error.code == "meta_transient"
    assert error.permanent is False
    assert error.detail == {
        "call": "campaign",
        "http_status": "500",
        "code": "2",
        "type": "OAuthException",
        "message": "Service unavailable",
    }


def _read(response: httpx.Response) -> AdsCallError:
    with pytest.raises(AdsCallError) as caught:
        read_body(response, CallContext(call="campaign", secrets=(TOKEN, "")))
    return caught.value


def test_body_that_is_not_an_error_object_keeps_a_stable_code() -> None:
    # Scenario: A body that is not an error object keeps a stable code
    not_json = _read(httpx.Response(400, text="<html>"))
    assert (not_json.code, not_json.permanent) == ("meta_transient", False)
    listed = _read(httpx.Response(200, json=[1]))
    assert (listed.code, listed.permanent) == ("meta_bad_body", True)
    bare = _read(httpx.Response(403, json={"error": "denied"}))
    assert (bare.code, bare.detail) == (
        "meta_403",
        {"call": "campaign", "http_status": "403"},
    )
    ok_text = _read(httpx.Response(200, text="ok"))
    assert ok_text.code == "meta_transient"


@pytest.mark.asyncio
async def test_created_object_without_an_id_names_the_call() -> None:
    # Scenario: Every failing call is named with Meta's error fields
    error = await _failed(
        Graph(fail={"adset": httpx.Response(200, json={"success": True})})
    )
    assert (error.code, error.detail) == ("meta_no_id", {"call": "adset"})


class _Clock:
    def now(self) -> datetime:
        return NOW


class _Msg:
    async def send(self, text: str, keyboard: InlineKeyboard) -> int | None:
        del text, keyboard
        return None

    async def edit(self, message_id: int, text: str) -> None:
        del message_id, text


@dataclass
class _Store:
    row: BoostRequest
    saves: list[StatusSave] = field(default_factory=list)

    async def by_key(self, key: str) -> BoostRequest | None:
        del key
        return None

    async def get(self, request_id: UUID) -> BoostRequest | None:
        del request_id
        return None

    async def media(self, media_id: str) -> MediaEligibility:
        del media_id
        return MediaEligibility(posted_at=None, product_type=None, permalink=None)

    async def open_exists(self, media_id: str) -> bool:
        del media_id
        return False

    async def pending_count(self) -> int:
        return 0

    async def committed_cents(self, since: datetime) -> int:
        del since
        return 0

    async def insert(self, request: BoostRequest) -> None:
        self.row = request

    async def list_requests(self, query: BoostListQuery) -> list[BoostRequest]:
        return [self.row] if self.row.status in query.statuses else []

    async def open_for(self, media_ids: tuple[str, ...]) -> dict[str, OpenBoost]:
        del media_ids
        return {}

    async def remember_message(self, request_id: UUID, message_id: int) -> None:
        del request_id, message_id

    async def save_status(self, change: StatusSave) -> None:
        self.saves.append(change)
        self.row = change.request

    async def commit(self) -> None:
        return None


def _limits() -> BoostLimits:
    return BoostLimits(
        requests_enabled=True,
        spend_enabled=True,
        max_daily_cents=3000,
        min_daily_cents=600,
        max_days=7,
        max_week_cents=10000,
        max_pending=3,
        max_age_days=30,
        allowed_countries=frozenset({"BR"}),
        approval_ttl_hours=12,
        currency="BRL",
        poll_minutes=60,
        max_attempts=5,
    )


@pytest.mark.asyncio
async def test_worker_stores_meta_details_on_the_failure_and_logs_them() -> None:
    # Scenario: The worker stores Meta's error details on the failure event and logs them
    store = _Store(row=request())
    graph = Graph(fail={"creative": meta_error(100, 1885183)})
    deps = BoostDeps(store=store, messenger=_Msg(), clock=_Clock(), owner_chat_id="1")
    tick = BoostTick(BoostTickDeps(boosts=deps, limits=_limits(), ads=gateway(graph)))
    with capture_logs() as logs:
        assert await tick.run() == 1
    assert store.row.status == STATUS_FAILED
    assert store.row.error_code == "meta_app_dev_mode"
    assert store.row.error_detail is not None
    assert store.row.error_detail["call"] == "creative"
    assert store.row.error_detail["fbtrace_id"] == "AbCdEf123"
    launch_logs = [entry for entry in logs if entry["event"] == "boost.launch"]
    assert len(launch_logs) == 1
    assert launch_logs[0]["error_code"] == "meta_app_dev_mode"
    assert launch_logs[0]["meta"]["error_subcode"] == "1885183"
    assert TOKEN not in json.dumps(logs, default=str)
