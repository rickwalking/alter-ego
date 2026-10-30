"""Boost policy, idempotency and the spend kill switch.

Gherkin: tests/features/autopilot_boost_approval.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from rag_backend.modules.autopilot.application.boost_actions import _stop
from rag_backend.modules.autopilot.application.boost_requests import (
    BoostDeps,
    BoostRequestService,
    CreateCommand,
    DecideCommand,
)
from rag_backend.modules.autopilot.application.boost_tick import (
    BoostTick,
    BoostTickDeps,
)
from rag_backend.modules.autopilot.boost_constants import (
    ERR_WEEK,
    HTTP_ACCEPTED,
    HTTP_UNPROCESSABLE,
    STATUS_APPROVED,
    STATUS_PENDING,
)
from rag_backend.modules.autopilot.domain.boost import (
    BoostAudience,
    BoostDraft,
    BoostError,
    BoostListQuery,
    BoostRequest,
    MediaEligibility,
    StatusSave,
    parse_boost_callback,
)
from rag_backend.modules.autopilot.domain.boost_policy import (
    BoostLimits,
    PolicyFacts,
    check_request,
)
from rag_backend.modules.autopilot.domain.ig_media import OpenBoost
from rag_backend.modules.autopilot.domain.messages import InlineKeyboard

_NOW = datetime(2026, 10, 29, 18, tzinfo=UTC)
_MEDIA = "18034567890123456"


def _limits() -> BoostLimits:
    return BoostLimits(
        requests_enabled=True,
        spend_enabled=False,
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


def _draft() -> BoostDraft:
    return BoostDraft(
        media_id=_MEDIA,
        daily_budget_cents=2000,
        days=1,
        objective="engagement",
        audience=BoostAudience(countries=("BR",), age_min=18, age_max=65),
        reason="Alcance acima da mediana da conta",
        score=1.6,
        start_at=None,
        idempotency_key="media-20261029",
    )


def test_weekly_cap_stores_nothing() -> None:
    # Scenario: Over the weekly cap
    facts = PolicyFacts(
        now=_NOW,
        committed_cents=9000,
        pending_count=0,
        media=MediaEligibility(
            posted_at=_NOW - timedelta(hours=47),
            product_type="FEED",
            permalink="https://instagram.example/p/1",
        ),
        open_exists=False,
    )
    with pytest.raises(BoostError) as caught:
        check_request(_draft(), _limits(), facts)
    assert caught.value.code == ERR_WEEK
    assert caught.value.status == HTTP_UNPROCESSABLE


def test_callback_regex_rejects_a_publish_button() -> None:
    assert parse_boost_callback("ap:approve:" + str(uuid4())) is None
    parsed = parse_boost_callback(f"ap:bst:ok:{uuid4()}")
    assert parsed is not None
    assert parsed.action == "ok"


class _Clock:
    def now(self) -> datetime:
        return _NOW


@dataclass
class _Msg:
    sent: int = 0

    async def send(self, text: str, keyboard: InlineKeyboard) -> int | None:
        del text, keyboard
        self.sent += 1
        return 7

    async def edit(self, message_id: int, text: str) -> None:
        del message_id, text


@dataclass
class _Store:
    rows: dict[str, BoostRequest] = field(default_factory=dict)
    by_id: dict[object, BoostRequest] = field(default_factory=dict)

    async def by_key(self, key: str) -> BoostRequest | None:
        return self.rows.get(key)

    async def get(self, request_id: object) -> BoostRequest | None:
        return self.by_id.get(request_id)

    async def media(self, media_id: str) -> MediaEligibility:
        del media_id
        return MediaEligibility(
            posted_at=_NOW - timedelta(hours=47),
            product_type="FEED",
            permalink="https://instagram.example/p/1",
        )

    async def open_exists(self, media_id: str) -> bool:
        del media_id
        return False

    async def pending_count(self) -> int:
        return 0

    async def committed_cents(self, since: datetime) -> int:
        del since
        return 0

    async def insert(self, request: BoostRequest) -> None:
        self.rows[request.idempotency_key] = request
        self.by_id[request.id] = request

    async def save_status(self, change: StatusSave) -> None:
        self.by_id[change.request.id] = change.request
        self.rows[change.request.idempotency_key] = change.request

    async def list_requests(self, query: BoostListQuery) -> list[BoostRequest]:
        rows = [row for row in self.by_id.values() if row.status in query.statuses]
        return rows[: query.limit]

    async def open_for(self, media_ids: tuple[str, ...]) -> dict[str, OpenBoost]:
        del media_ids
        return {}

    async def remember_message(self, request_id: object, message_id: int) -> None:
        row = self.by_id[request_id]
        self.by_id[request_id] = replace(row, telegram_message_id=message_id)

    async def commit(self) -> None:
        return None


@dataclass
class _Ads:
    calls: int = 0

    async def launch(self, request: BoostRequest) -> BoostRequest:
        self.calls += 1
        return request

    async def pause(self, campaign_id: str) -> None:
        del campaign_id
        self.calls += 1


def _service(store: _Store, msg: _Msg) -> BoostRequestService:
    return BoostRequestService(
        BoostDeps(
            store=store,
            messenger=msg,
            clock=_Clock(),
            owner_chat_id="1",
        )
    )


@pytest.mark.asyncio
async def test_create_is_pending_and_messages_the_owner() -> None:
    # Scenario: Bot requests a boost and the owner approves
    store = _Store()
    msg = _Msg()
    created = await _service(store, msg).create(
        CreateCommand(draft=_draft(), limits=_limits())
    )
    assert created.status == HTTP_ACCEPTED
    assert created.request.status == STATUS_PENDING
    assert msg.sent == 1
    decided = await _service(store, msg).decide(
        DecideCommand(
            request_id=created.request.id,
            approve=True,
            actor="owner:1",
            limits=_limits(),
        )
    )
    assert decided.status == STATUS_APPROVED


@pytest.mark.asyncio
async def test_kill_switch_makes_no_ads_call() -> None:
    # Scenario: Kill switch blocks spending
    store = _Store()
    msg = _Msg()
    created = await _service(store, msg).create(
        CreateCommand(draft=_draft(), limits=_limits())
    )
    approved = replace(created.request, status=STATUS_APPROVED)
    await store.save_status(
        StatusSave(previous=STATUS_PENDING, request=approved, actor="owner:1")
    )
    ads = _Ads()
    count = await BoostTick(
        BoostTickDeps(
            boosts=BoostDeps(
                store=store, messenger=msg, clock=_Clock(), owner_chat_id="1"
            ),
            limits=_limits(),
            ads=ads,
        )
    ).run()
    assert ads.calls == 0
    assert count == 0


@dataclass
class _Pauser:
    ok: bool
    calls: list[str] = field(default_factory=list)

    async def pause(self, campaign_id: str) -> bool:
        self.calls.append(campaign_id)
        return self.ok


class _StopDeps:
    def __init__(self, store: _Store, pauser: _Pauser) -> None:
        self.boosts = store
        self.boost_limits = _limits()
        self.pauser = pauser
        self.messenger = _Msg()
        self.clock = _Clock()
        self.owner_chat_id = "1"


@pytest.mark.asyncio
async def test_stop_pauses_the_live_campaign() -> None:
    store = _Store()
    msg = _Msg()
    created = await _service(store, msg).create(
        CreateCommand(draft=_draft(), limits=_limits())
    )
    active = replace(
        created.request,
        status="active",
        meta_campaign_id="camp-1",
    )
    await store.save_status(
        StatusSave(previous=STATUS_PENDING, request=active, actor="worker")
    )
    pauser = _Pauser(ok=True)
    await _stop(_StopDeps(store, pauser), created.request.id)
    assert pauser.calls == ["camp-1"]
    assert store.by_id[created.request.id].status == "stopped"
