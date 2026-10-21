"""Daily Instagram refresh and the owner alert.

Gherkin: tests/features/autopilot_ig_token.feature
"""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from urllib.parse import unquote

import httpx
import pytest
import respx
import structlog

from rag_backend.modules.autopilot.application.day_gate import SaoPauloDayGate
from rag_backend.modules.autopilot.application.token_refresher import (
    TokenRefresher,
    TokenRefresherDependencies,
)
from rag_backend.modules.autopilot.credential_constants import (
    GRAPH_ACCESS_PARAM,
    IG_REFRESH_URL,
    IG_REGENERATION_DOC,
    LOG_CREDENTIAL_ALERT_FAILED,
    META_ERROR_INVALID_TOKEN,
    PROVIDER_INSTAGRAM,
)
from rag_backend.modules.autopilot.domain.credential_ports import (
    PlainCredential,
    WriteCredential,
)
from rag_backend.modules.autopilot.infrastructure.instagram_token_client import (
    HttpxInstagramTokenClient,
)
from rag_backend.modules.autopilot.infrastructure.token_alert import (
    TelegramAlertConfig,
    TelegramTokenAlerter,
)

_NOW = datetime(2026, 10, 14, 15, tzinfo=UTC)
_PLAIN = "plain token ! secret"
_NEW = "refreshed token ! secret"
_EXPIRES_IN = 5_184_000


class _Store:
    def __init__(self, row: PlainCredential | None) -> None:
        self.row = row
        self.writes = 0

    async def exists(self, provider: str) -> bool:
        return self.row is not None and self.row.provider == provider

    async def read(self, provider: str) -> PlainCredential | None:
        if self.row is None or self.row.provider != provider:
            return None
        return self.row

    async def write(self, command: WriteCredential) -> None:
        self.writes += 1
        self.row = PlainCredential(
            provider=command.provider,
            token=command.token,
            expires_at=command.expires_at,
            refreshed_at=command.refreshed_at,
        )


class _Alerts:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        self.messages.append(message)


class _Clock:
    def __init__(self, now: datetime) -> None:
        self.now_value = now

    def now(self) -> datetime:
        return self.now_value


def _row(*, refreshed_days_ago: int, expires_in_days: int) -> PlainCredential:
    return PlainCredential(
        provider=PROVIDER_INSTAGRAM,
        token=_PLAIN,
        refreshed_at=_NOW - timedelta(days=refreshed_days_ago),
        expires_at=_NOW + timedelta(days=expires_in_days),
    )


def _refresher(
    store: _Store,
    alerts: _Alerts,
    clock: _Clock,
    gate: SaoPauloDayGate,
) -> TokenRefresher:
    return TokenRefresher(
        TokenRefresherDependencies(
            store=store,
            client=HttpxInstagramTokenClient(),
            alerter=alerts,
            clock=clock,
            gate=gate,
        )
    )


@pytest.mark.asyncio
async def test_fifty_one_day_token_is_refreshed_and_expiry_moves_forward() -> None:
    """Scenario: Token refreshed before expiry."""
    store = _Store(_row(refreshed_days_ago=51, expires_in_days=9))
    previous = store.row
    assert previous is not None
    alerts = _Alerts()
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        assert request.url.params[GRAPH_ACCESS_PARAM] == _PLAIN
        return httpx.Response(
            200,
            json={
                "access_token": _NEW,
                "token_type": "bearer",
                "expires_in": _EXPIRES_IN,
            },
        )

    with respx.mock(assert_all_called=True) as router:
        router.get(IG_REFRESH_URL).mock(side_effect=handler)
        changed = await _refresher(
            store, alerts, _Clock(_NOW), SaoPauloDayGate()
        ).tick()
    assert changed == 1
    assert calls["count"] == 1
    assert store.row is not None
    assert store.row.token == _NEW
    assert store.row.expires_at == _NOW + timedelta(seconds=_EXPIRES_IN)
    assert previous.expires_at is not None
    assert store.row.expires_at > previous.expires_at
    assert alerts.messages == []


@pytest.mark.asyncio
async def test_a_fresh_token_is_not_refreshed() -> None:
    store = _Store(_row(refreshed_days_ago=1, expires_in_days=40))
    alerts = _Alerts()

    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("refresh called")

    with respx.mock(assert_all_called=False) as router:
        router.get(IG_REFRESH_URL).mock(side_effect=handler)
        changed = await _refresher(
            store, alerts, _Clock(_NOW), SaoPauloDayGate()
        ).tick()
    assert changed == 0
    assert alerts.messages == []
    assert store.writes == 0


@pytest.mark.asyncio
async def test_refresh_runs_once_on_the_same_day() -> None:
    """Scenario: Refresh runs once per day."""
    store = _Store(_row(refreshed_days_ago=51, expires_in_days=9))
    alerts = _Alerts()
    gate = SaoPauloDayGate()
    clock = _Clock(_NOW)
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(
            200,
            json={"access_token": _NEW, "expires_in": _EXPIRES_IN},
        )

    with respx.mock(assert_all_called=False) as router:
        router.get(IG_REFRESH_URL).mock(side_effect=handler)
        refresher = _refresher(store, alerts, clock, gate)
        assert await refresher.tick() == 1
        assert await refresher.tick() == 0
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_near_expiry_failure_alerts_once_per_day() -> None:
    """Scenario: Refresh keeps failing near expiry.
    Scenario: Expiry alert is once per day.
    """
    store = _Store(_row(refreshed_days_ago=10, expires_in_days=5))
    alerts = _Alerts()
    gate = SaoPauloDayGate()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503, json={"error": {"message": "unavailable", "code": 2}}
        )

    with respx.mock(assert_all_called=False) as router:
        router.get(IG_REFRESH_URL).mock(side_effect=handler)
        refresher = _refresher(store, alerts, _Clock(_NOW), gate)
        assert await refresher.tick() == 0
        assert await refresher.tick() == 0
    assert store.writes == 0
    assert store.row is not None
    assert store.row.token == _PLAIN
    assert len(alerts.messages) == 1
    assert "5" in alerts.messages[0]
    assert IG_REGENERATION_DOC in alerts.messages[0]
    assert _PLAIN not in alerts.messages[0]


@pytest.mark.asyncio
async def test_failed_refresh_is_retried_the_next_day() -> None:
    """Scenario: Failed refresh is retried the next day."""
    store = _Store(_row(refreshed_days_ago=10, expires_in_days=5))
    alerts = _Alerts()
    gate = SaoPauloDayGate()
    clock = _Clock(_NOW)
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(503, json={"error": {"code": 2}})

    with respx.mock(assert_all_called=False) as router:
        router.get(IG_REFRESH_URL).mock(side_effect=handler)
        refresher = _refresher(store, alerts, clock, gate)
        await refresher.tick()
        clock.now_value = _NOW + timedelta(days=1)
        await refresher.tick()
    assert calls["count"] == 2
    assert len(alerts.messages) == 2


@pytest.mark.asyncio
async def test_error_190_alerts_without_storing_a_new_token() -> None:
    """Scenario: Invalid token alerts even when expiry is far."""
    store = _Store(_row(refreshed_days_ago=51, expires_in_days=30))
    alerts = _Alerts()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"message": "Invalid OAuth access token.", "code": 190}},
        )

    with respx.mock(assert_all_called=True) as router:
        router.get(IG_REFRESH_URL).mock(side_effect=handler)
        await _refresher(store, alerts, _Clock(_NOW), SaoPauloDayGate()).tick()
    assert store.writes == 0
    assert len(alerts.messages) == 1
    assert str(META_ERROR_INVALID_TOKEN) in alerts.messages[0]
    assert IG_REGENERATION_DOC in alerts.messages[0]


@pytest.mark.asyncio
async def test_distant_failure_does_not_alert() -> None:
    store = _Store(_row(refreshed_days_ago=51, expires_in_days=30))
    alerts = _Alerts()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"code": 1}})

    with respx.mock(assert_all_called=True) as router:
        router.get(IG_REFRESH_URL).mock(side_effect=handler)
        await _refresher(store, alerts, _Clock(_NOW), SaoPauloDayGate()).tick()
    assert alerts.messages == []
    assert store.writes == 0


@pytest.mark.asyncio
async def test_refresh_logs_do_not_contain_the_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Token is never logged."""
    buffer = io.StringIO()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(file=buffer),
        cache_logger_on_first_use=False,
    )
    import rag_backend.modules.autopilot.application.token_refresher as refresher_module

    monkeypatch.setattr(refresher_module, "logger", structlog.get_logger())
    store = _Store(_row(refreshed_days_ago=51, expires_in_days=9))
    alerts = _Alerts()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"access_token": _NEW, "expires_in": _EXPIRES_IN},
        )

    try:
        with respx.mock(assert_all_called=True) as router:
            router.get(IG_REFRESH_URL).mock(side_effect=handler)
            await _refresher(store, alerts, _Clock(_NOW), SaoPauloDayGate()).tick()
    finally:
        structlog.reset_defaults()
    rendered = buffer.getvalue()
    assert _PLAIN not in rendered
    assert _NEW not in rendered


@pytest.mark.asyncio
async def test_telegram_alert_posts_the_doc_link_and_not_the_token() -> None:
    """Scenario: Refresh keeps failing near expiry."""
    message = f"expires in 5 days. {IG_REGENERATION_DOC}"
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.content.decode())
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 9}})

    with respx.mock(assert_all_called=True) as router:
        router.post(url__regex=r".*sendMessage$").mock(side_effect=handler)
        await TelegramTokenAlerter(
            TelegramAlertConfig(bot_token="bot-secret", chat_id="42")
        ).send(message)
    assert len(seen) == 1
    assert IG_REGENERATION_DOC in unquote(seen[0])
    assert _PLAIN not in seen[0]


@pytest.mark.asyncio
async def test_unconfigured_telegram_does_not_call() -> None:
    with respx.mock(assert_all_called=False) as router:
        route = router.post(url__regex=r".*sendMessage$").mock(
            return_value=httpx.Response(
                200, json={"ok": True, "result": {"message_id": 1}}
            )
        )
        await TelegramTokenAlerter(
            TelegramAlertConfig(bot_token="", chat_id="42")
        ).send("hello")
    assert route.call_count == 0


@pytest.mark.asyncio
async def test_telegram_failure_is_swallowed_without_logging_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    buffer = io.StringIO()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(file=buffer),
        cache_logger_on_first_use=False,
    )
    import rag_backend.modules.autopilot.infrastructure.token_alert as alert_module

    monkeypatch.setattr(alert_module, "logger", structlog.get_logger())
    try:
        with respx.mock(assert_all_called=True) as router:
            router.post(url__regex=r".*sendMessage$").mock(
                return_value=httpx.Response(500, text="bot-secret " + _PLAIN)
            )
            await TelegramTokenAlerter(
                TelegramAlertConfig(bot_token="bot-secret", chat_id="42")
            ).send("expires in 5 days")
    finally:
        structlog.reset_defaults()
    rendered = buffer.getvalue()
    assert LOG_CREDENTIAL_ALERT_FAILED in rendered
    assert "bot-secret" not in rendered
    assert _PLAIN not in rendered
