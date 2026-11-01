"""A boost without a Meta Page or Instagram user id fails before any Graph call.

Gherkin: tests/features/boost_meta_page_missing_ae0586.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

from rag_backend.modules.autopilot.application.boost_requests import BoostDeps
from rag_backend.modules.autopilot.application.boost_tick import (
    BoostTick,
    BoostTickDeps,
)
from rag_backend.modules.autopilot.boost_constants import (
    ERR_ADS_DISABLED,
    ERR_PAGE_MISSING,
    STATUS_APPROVED,
    STATUS_FAILED,
)
from rag_backend.modules.autopilot.domain.boost import (
    BoostAudience,
    BoostListQuery,
    BoostRequest,
    StatusSave,
)
from rag_backend.modules.autopilot.domain.boost_policy import BoostLimits
from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.infrastructure.meta_ads_gateway import (
    AdsCallError,
    AdsConfig,
    MetaAdsGateway,
)

_NOW = datetime(2026, 10, 31, 12, tzinfo=UTC)
_PAGE = "1122334455"
_IG_USER = "17841400000000000"


def _config(*, page_id: str, ig_user_id: str, enabled: bool = True) -> AdsConfig:
    return AdsConfig(
        enabled=enabled,
        token="ads-token",
        app_secret="app-secret",
        account_id="987",
        page_id=page_id,
        ig_user_id=ig_user_id,
        graph_base="https://graph.example/v21.0",
    )


def _request() -> BoostRequest:
    return BoostRequest(
        id=uuid4(),
        idempotency_key="media-20261031",
        request_hash="hash",
        media_id="18034567890123456",
        status=STATUS_APPROVED,
        objective="engagement",
        daily_budget_cents=2000,
        days=1,
        total_budget_cents=2000,
        currency="BRL",
        audience=BoostAudience(countries=("BR",), age_min=18, age_max=65),
        reason="Alcance acima da mediana da conta",
        score=1.6,
        created_at=_NOW,
        expires_at=_NOW + timedelta(hours=12),
    )


@dataclass
class _Graph:
    calls: list[str] = field(default_factory=list)

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append(f"{request.method} {path}")
        if path.endswith("/minimum_budgets"):
            return httpx.Response(200, json={})
        if path.endswith("/act_987"):
            return httpx.Response(200, json={"account_status": 1})
        if request.method == "POST" and "/act_987/" in path:
            return httpx.Response(200, json={"id": f"id-{len(self.calls)}"})
        if request.method == "POST":
            return httpx.Response(200, json={"success": True})
        return httpx.Response(200, json={"id": "18034567890123456"})


def _gateway(config: AdsConfig, graph: _Graph) -> MetaAdsGateway:
    client = httpx.AsyncClient(transport=httpx.MockTransport(graph.handle))
    return MetaAdsGateway(config, client)


@pytest.mark.asyncio
async def test_empty_page_id_fails_before_any_meta_call() -> None:
    # Scenario: An empty Page id fails the launch before any Meta call
    graph = _Graph()
    gateway = _gateway(_config(page_id="", ig_user_id=_IG_USER), graph)
    with pytest.raises(AdsCallError) as caught:
        await gateway.launch(_request())
    assert caught.value.code == ERR_PAGE_MISSING
    assert caught.value.permanent is True
    assert graph.calls == []


@pytest.mark.asyncio
async def test_blank_instagram_user_id_fails_before_any_meta_call() -> None:
    # Scenario: An empty Instagram user id fails the launch before any Meta call
    graph = _Graph()
    gateway = _gateway(_config(page_id=_PAGE, ig_user_id="   "), graph)
    with pytest.raises(AdsCallError) as caught:
        await gateway.launch(_request())
    assert caught.value.code == ERR_PAGE_MISSING
    assert caught.value.permanent is True
    assert graph.calls == []


@pytest.mark.asyncio
async def test_configured_page_still_reaches_meta() -> None:
    # Scenario: A configured Page still reaches the Marketing API
    graph = _Graph()
    gateway = _gateway(_config(page_id=_PAGE, ig_user_id=_IG_USER), graph)
    launched = await gateway.launch(_request())
    assert launched.meta_creative_id is not None
    assert launched.meta_ad_id is not None
    assert len(graph.calls) == 10
    assert graph.calls[0].startswith("GET ")
    assert graph.calls[5] == "POST /v21.0/act_987/adcreatives"


@pytest.mark.asyncio
async def test_kill_switch_wins_over_a_missing_page() -> None:
    # Scenario: The kill switch wins over a missing Page
    graph = _Graph()
    gateway = _gateway(_config(page_id="", ig_user_id="", enabled=False), graph)
    with pytest.raises(AdsCallError) as caught:
        await gateway.launch(_request())
    assert caught.value.code == ERR_ADS_DISABLED
    assert graph.calls == []


class _Clock:
    def now(self) -> datetime:
        return _NOW


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
    commits: int = 0

    async def list_requests(self, query: BoostListQuery) -> list[BoostRequest]:
        return [self.row] if self.row.status in query.statuses else []

    async def save_status(self, change: StatusSave) -> None:
        self.saves.append(change)
        self.row = change.request

    async def commit(self) -> None:
        self.commits += 1


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
async def test_worker_stores_the_boost_as_failed_with_meta_page_missing() -> None:
    # Scenario: The worker stores the boost as failed with meta_page_missing
    graph = _Graph()
    store = _Store(row=_request())
    tick = BoostTick(
        BoostTickDeps(
            boosts=BoostDeps(
                store=store,  # type: ignore[arg-type]
                messenger=_Msg(),
                clock=_Clock(),
                owner_chat_id="1",
            ),
            limits=_limits(),
            ads=_gateway(_config(page_id="", ig_user_id=_IG_USER), graph),
        )
    )
    assert await tick.run() == 1
    assert store.row.status == STATUS_FAILED
    assert store.row.error_code == ERR_PAGE_MISSING
    assert store.commits == 1
    assert graph.calls == []
