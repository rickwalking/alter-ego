"""Instagram token clocks, Graph parsing, and the refresh client.

Gherkin: tests/features/autopilot_ig_token.feature
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from rag_backend.modules.autopilot.credential_constants import (
    EXPIRY_ALERT_WINDOW_DAYS,
    EXPIRY_REFRESH_WINDOW_DAYS,
    GRANT_TYPE_IG_REFRESH,
    GRAPH_ACCESS_PARAM,
    IG_REFRESH_URL,
    IG_REGENERATION_DOC,
    META_ERROR_INVALID_TOKEN,
    PARAM_GRANT_TYPE,
    REFRESH_AFTER_DAYS,
    SEED_LIFETIME_DAYS,
)
from rag_backend.modules.autopilot.domain.credential_ports import (
    PlainCredential,
    RefreshRequest,
    TokenRefreshError,
)
from rag_backend.modules.autopilot.domain.token_refresh import (
    AlertFacts,
    alert_message,
    parse_refresh_response,
    refresh_due,
    seed_window,
)
from rag_backend.modules.autopilot.infrastructure.instagram_token_client import (
    HttpxInstagramTokenClient,
)

_NOW = datetime(2026, 10, 14, 15, tzinfo=UTC)
_PLAIN = "plain token ! secret"
_NEW = "refreshed token ! secret"


def _credential(
    *,
    refreshed_days_ago: int | None,
    expires_in_days: int | None,
) -> PlainCredential:
    refreshed = None
    if refreshed_days_ago is not None:
        refreshed = _NOW - timedelta(days=refreshed_days_ago)
    expires = None
    if expires_in_days is not None:
        expires = _NOW + timedelta(days=expires_in_days)
    return PlainCredential(
        provider="instagram",
        token=_PLAIN,
        expires_at=expires,
        refreshed_at=refreshed,
    )


def test_seed_window_is_sixty_days_and_starts_the_refresh_clock() -> None:
    """Scenario: Env token seeds the store once."""
    window = seed_window(_NOW)
    assert window.expires_at - _NOW == timedelta(days=SEED_LIFETIME_DAYS)
    assert window.refreshed_at == _NOW


def test_token_fifty_days_old_is_due() -> None:
    """Scenario: Token refreshed before expiry. Age of 50 days is due."""
    credential = _credential(refreshed_days_ago=REFRESH_AFTER_DAYS, expires_in_days=20)
    assert refresh_due(credential, _NOW)


def test_token_younger_than_fifty_days_with_distant_expiry_is_not_due() -> None:
    credential = _credential(
        refreshed_days_ago=REFRESH_AFTER_DAYS - 1,
        expires_in_days=EXPIRY_REFRESH_WINDOW_DAYS,
    )
    assert not refresh_due(credential, _NOW)


def test_expiry_inside_ten_days_is_due_even_when_recently_refreshed() -> None:
    credential = _credential(
        refreshed_days_ago=1,
        expires_in_days=EXPIRY_REFRESH_WINDOW_DAYS - 1,
    )
    assert refresh_due(credential, _NOW)


def test_missing_clocks_are_not_due() -> None:
    credential = _credential(refreshed_days_ago=None, expires_in_days=None)
    assert not refresh_due(credential, _NOW)


def test_alert_names_five_days_and_the_regeneration_doc() -> None:
    """Scenario: Refresh keeps failing near expiry."""
    message = alert_message(
        AlertFacts(error_code=400, expires_at=_NOW + timedelta(days=5), now=_NOW)
    )
    assert message is not None
    assert "5" in message
    assert IG_REGENERATION_DOC in message
    assert _PLAIN not in message


def test_exact_seven_day_expiry_stays_silent() -> None:
    message = alert_message(
        AlertFacts(
            error_code=500,
            expires_at=_NOW + timedelta(days=EXPIRY_ALERT_WINDOW_DAYS),
            now=_NOW,
        )
    )
    assert message is None


def test_error_190_alerts_when_expiry_is_far() -> None:
    """Scenario: Invalid token alerts even when expiry is far."""
    message = alert_message(
        AlertFacts(
            error_code=META_ERROR_INVALID_TOKEN,
            expires_at=_NOW + timedelta(days=30),
            now=_NOW,
        )
    )
    assert message is not None
    assert str(META_ERROR_INVALID_TOKEN) in message
    assert IG_REGENERATION_DOC in message


def test_error_190_near_expiry_mentions_both() -> None:
    message = alert_message(
        AlertFacts(
            error_code=META_ERROR_INVALID_TOKEN,
            expires_at=_NOW + timedelta(days=5),
            now=_NOW,
        )
    )
    assert message is not None
    assert str(META_ERROR_INVALID_TOKEN) in message
    assert "5" in message


def test_parse_grant_and_reject_a_body_without_expiry() -> None:
    grant = parse_refresh_response(
        200,
        '{"access_token": "next", "expires_in": 5184000}',
    )
    assert grant.access_token == "next"
    assert grant.expires_in == 5184000
    with pytest.raises(TokenRefreshError) as caught:
        parse_refresh_response(200, '{"access_token": "next"}')
    assert _PLAIN not in str(caught.value)


def test_parse_reads_meta_error_190() -> None:
    with pytest.raises(TokenRefreshError) as caught:
        parse_refresh_response(
            400,
            '{"error": {"message": "bad", "code": 190}}',
        )
    assert caught.value.error_code == META_ERROR_INVALID_TOKEN
    assert caught.value.status_code == 400


@pytest.mark.asyncio
async def test_client_calls_the_unversioned_refresh_endpoint() -> None:
    """Scenario: Token refreshed before expiry."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params[PARAM_GRANT_TYPE] == GRANT_TYPE_IG_REFRESH
        assert request.url.params[GRAPH_ACCESS_PARAM] == _PLAIN
        return httpx.Response(
            200,
            json={"access_token": _NEW, "token_type": "bearer", "expires_in": 60},
        )

    with respx.mock(assert_all_called=True) as router:
        router.get(IG_REFRESH_URL).mock(side_effect=handler)
        grant = await HttpxInstagramTokenClient().refresh(RefreshRequest(token=_PLAIN))
    assert grant.access_token == _NEW
    assert grant.expires_in == 60


@pytest.mark.asyncio
async def test_client_hides_the_token_when_graph_returns_190() -> None:
    """Scenario: Invalid token alerts even when expiry is far."""
    body = '{"error": {"message": "Invalid OAuth access token.", "code": 190}}'
    with respx.mock(assert_all_called=True) as router:
        router.get(IG_REFRESH_URL).mock(return_value=httpx.Response(400, text=body))
        with pytest.raises(TokenRefreshError) as caught:
            await HttpxInstagramTokenClient().refresh(RefreshRequest(token=_PLAIN))
    assert caught.value.error_code == META_ERROR_INVALID_TOKEN
    assert _PLAIN not in str(caught.value)
    assert caught.value.__cause__ is None


@pytest.mark.asyncio
async def test_client_transport_error_has_no_token_and_no_cause() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed")

    with respx.mock(assert_all_called=True) as router:
        router.get(IG_REFRESH_URL).mock(side_effect=handler)
        with pytest.raises(TokenRefreshError) as caught:
            await HttpxInstagramTokenClient().refresh(RefreshRequest(token=_PLAIN))
    assert caught.value.status_code == 0
    assert caught.value.error_code is None
    assert _PLAIN not in str(caught.value)
    assert caught.value.__cause__ is None


@pytest.mark.asyncio
async def test_client_does_not_follow_redirects() -> None:
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(302, headers={"location": "https://example.invalid/x"})

    with respx.mock(assert_all_called=False) as router:
        router.get(IG_REFRESH_URL).mock(side_effect=handler)
        with pytest.raises(TokenRefreshError) as caught:
            await HttpxInstagramTokenClient().refresh(RefreshRequest(token=_PLAIN))
    assert calls["count"] == 1
    assert caught.value.status_code == 302
    assert _PLAIN not in str(caught.value)
