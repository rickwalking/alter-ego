"""Pure Instagram token clocks and Graph refresh parsing. No I/O."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast

from rag_backend.modules.autopilot.constants import HTTP_SUCCESS_MAX, HTTP_SUCCESS_MIN
from rag_backend.modules.autopilot.credential_constants import (
    ALERT_BOTH,
    ALERT_EXPIRING,
    ALERT_INVALID,
    EXPIRY_ALERT_WINDOW_DAYS,
    EXPIRY_REFRESH_WINDOW_DAYS,
    FIELD_CODE,
    FIELD_ERROR,
    FIELD_EXPIRES_IN,
    GRAPH_ACCESS_PARAM,
    IG_REGENERATION_DOC,
    META_ERROR_INVALID_TOKEN,
    REFRESH_AFTER_DAYS,
    SECONDS_PER_DAY,
    SEED_LIFETIME_DAYS,
    TEXT_ALERT_BOTH,
    TEXT_ALERT_EXPIRING,
    TEXT_ALERT_INVALID,
)
from rag_backend.modules.autopilot.domain.credential_ports import (
    PlainCredential,
    RefreshGrant,
    TokenRefreshError,
)
from rag_backend.modules.autopilot.domain.topic_text import as_utc


@dataclass(frozen=True, kw_only=True)
class SeedWindow:
    """Clocks written when the env token is inserted for the first time."""

    expires_at: datetime
    refreshed_at: datetime


@dataclass(frozen=True, kw_only=True)
class AlertFacts:
    """What a failed refresh knows. The token itself is not included."""

    error_code: int | None
    expires_at: datetime | None
    now: datetime


def seed_window(now: datetime) -> SeedWindow:
    """Conservative 60-day expiry, with the 50-day clock starting at ``now``."""
    moment = as_utc(now)
    return SeedWindow(
        expires_at=moment + timedelta(days=SEED_LIFETIME_DAYS),
        refreshed_at=moment,
    )


def refresh_due(credential: PlainCredential, now: datetime) -> bool:
    """True when the token is at least 50 days old or expires within 10 days."""
    if _refreshed_due(credential.refreshed_at, now):
        return True
    return _expires_within(credential.expires_at, now, EXPIRY_REFRESH_WINDOW_DAYS)


def expiry_after_grant(now: datetime, expires_in: int) -> datetime:
    """``expires_at`` stored from Graph's ``expires_in`` seconds."""
    return as_utc(now) + timedelta(seconds=expires_in)


def alert_message(facts: AlertFacts) -> str | None:
    """Owner text, or None when this failure should stay silent."""
    kind = _alert_kind(facts)
    if kind is None:
        return None
    builder = _ALERTS[kind]
    return builder(facts)


def parse_refresh_response(status_code: int, body: str) -> RefreshGrant:
    """Return the new grant, or raise when Graph did not issue one."""
    code = _error_code(body)
    if not _http_ok(status_code):
        raise TokenRefreshError(status_code=status_code, error_code=code)
    grant = _grant(body)
    if grant is None:
        raise TokenRefreshError(status_code=status_code, error_code=code)
    return grant


def _refreshed_due(refreshed_at: datetime | None, now: datetime) -> bool:
    if refreshed_at is None:
        return False
    age = as_utc(now) - as_utc(refreshed_at)
    return age >= timedelta(days=REFRESH_AFTER_DAYS)


def _expires_within(expires_at: datetime | None, now: datetime, days: int) -> bool:
    if expires_at is None:
        return False
    horizon = as_utc(now) + timedelta(days=days)
    return as_utc(expires_at) < horizon


def _alert_kind(facts: AlertFacts) -> str | None:
    invalid = facts.error_code == META_ERROR_INVALID_TOKEN
    expiring = _expires_within(facts.expires_at, facts.now, EXPIRY_ALERT_WINDOW_DAYS)
    if invalid and expiring:
        return ALERT_BOTH
    if invalid:
        return ALERT_INVALID
    if expiring:
        return ALERT_EXPIRING
    return None


def _days(facts: AlertFacts) -> int:
    if facts.expires_at is None:
        return 0
    seconds = (as_utc(facts.expires_at) - as_utc(facts.now)).total_seconds()
    if seconds <= 0:
        return 0
    return int(seconds // SECONDS_PER_DAY)


def _expiring(facts: AlertFacts) -> str:
    return TEXT_ALERT_EXPIRING.format(days=_days(facts), link=IG_REGENERATION_DOC)


def _invalid(_facts: AlertFacts) -> str:
    return TEXT_ALERT_INVALID.format(
        code=META_ERROR_INVALID_TOKEN,
        link=IG_REGENERATION_DOC,
    )


def _both(facts: AlertFacts) -> str:
    return TEXT_ALERT_BOTH.format(
        code=META_ERROR_INVALID_TOKEN,
        days=_days(facts),
        link=IG_REGENERATION_DOC,
    )


_ALERTS: dict[str, Callable[[AlertFacts], str]] = {
    ALERT_EXPIRING: _expiring,
    ALERT_INVALID: _invalid,
    ALERT_BOTH: _both,
}


def _http_ok(status_code: int) -> bool:
    return HTTP_SUCCESS_MIN <= status_code < HTTP_SUCCESS_MAX


def _error_code(body: str) -> int | None:
    payload = _object(body)
    if payload is None:
        return None
    error = payload.get(FIELD_ERROR)
    if not isinstance(error, dict):
        return None
    return _positive_int(cast(dict[str, object], error).get(FIELD_CODE))


def _grant(body: str) -> RefreshGrant | None:
    payload = _object(body)
    if payload is None:
        return None
    token = payload.get(GRAPH_ACCESS_PARAM)
    expires_in = _positive_int(payload.get(FIELD_EXPIRES_IN))
    if not isinstance(token, str) or not token or expires_in is None:
        return None
    return RefreshGrant(access_token=token, expires_in=expires_in)


def _object(body: str) -> dict[str, object] | None:
    try:
        parsed = cast(object, json.loads(body))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return cast(dict[str, object], parsed)


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value <= 0:
        return None
    return value
