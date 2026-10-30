"""Branches the diff-cover gate still needed on the insights and boost paths.

Gherkin: tests/features/autopilot_ig_insights.feature
Gherkin: tests/features/autopilot_boost_approval.feature
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from rag_backend.modules.autopilot.api.auth import require_autopilot_api_key
from rag_backend.modules.autopilot.api.ig_insights import router
from rag_backend.modules.autopilot.boost_constants import (
    ERR_AUDIENCE,
    ERR_COUNTRY,
    ERR_DAILY_OVER,
    ERR_DAILY_UNDER,
    ERR_DAYS,
    ERR_DISABLED,
    ERR_MEDIA,
    ERR_OBJECTIVE,
    ERR_OPEN,
    ERR_PENDING,
    STATUS_ACTIVE,
    STATUS_PENDING,
)
from rag_backend.modules.autopilot.domain.boost import (
    BoostAudience,
    BoostDraft,
    BoostError,
    IllegalBoostTransitionError,
    MediaEligibility,
    parse_idempotency_key,
)
from rag_backend.modules.autopilot.domain.boost_policy import (
    BoostLimits,
    PolicyFacts,
    check_request,
)
from rag_backend.modules.autopilot.domain.boost_state import assert_transition
from rag_backend.modules.autopilot.domain.ig_insights_query import (
    IgInsightsQueryError,
    media_type_or_raise,
    parse_limit,
    parse_refresh,
    parse_timestamp,
    product_type_or_raise,
    resolve_query,
)
from rag_backend.modules.autopilot.domain.ig_media import IgInsightsRequest
from rag_backend.modules.autopilot.ig_media_constants import (
    ERR_LIMIT_INVALID,
    ERR_MEDIA_TYPE_INVALID,
    ERR_PRODUCT_TYPE_INVALID,
    ERR_REFRESH_INVALID,
    ERR_TIMESTAMP_INVALID,
    ERR_WINDOW_INVALID,
    IG_INSIGHTS_DEFAULT_LIMIT,
    IG_INSIGHTS_MAX_LIMIT,
    IG_INSIGHTS_MAX_SINCE_DAYS,
    MEDIA_IMAGE,
    PRODUCT_FEED,
    PRODUCT_STORY,
)

_NOW = datetime(2026, 10, 29, 18, tzinfo=UTC)
_MEDIA = "18034567890123456"
_KEY = "media-20261029"


def test_missing_api_key_is_a_router_dependency() -> None:
    # Scenario: Missing API key
    dependencies = [item.dependency for item in router.dependencies]
    assert require_autopilot_api_key in dependencies


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
        idempotency_key=_KEY,
    )


def _facts() -> PolicyFacts:
    return PolicyFacts(
        now=_NOW,
        committed_cents=0,
        pending_count=0,
        media=MediaEligibility(
            posted_at=_NOW, product_type=PRODUCT_FEED, permalink=None
        ),
        open_exists=False,
    )


def _rejected(draft: BoostDraft, facts: PolicyFacts, limits: BoostLimits) -> str:
    with pytest.raises(BoostError) as caught:
        check_request(draft, limits, facts)
    return caught.value.code


def test_disabled_requests_are_refused() -> None:
    limits = replace(_limits(), requests_enabled=False)
    assert _rejected(_draft(), _facts(), limits) == ERR_DISABLED


def test_shape_rejections() -> None:
    limits = _limits()
    facts = _facts()
    assert _rejected(replace(_draft(), objective="awareness"), facts, limits) == (
        ERR_OBJECTIVE
    )
    over = replace(_draft(), daily_budget_cents=limits.max_daily_cents + 1)
    assert _rejected(over, facts, limits) == ERR_DAILY_OVER
    under = replace(_draft(), daily_budget_cents=limits.min_daily_cents - 1)
    assert _rejected(under, facts, limits) == ERR_DAILY_UNDER
    assert _rejected(replace(_draft(), days=limits.max_days + 1), facts, limits) == (
        ERR_DAYS
    )


def test_audience_rejections() -> None:
    limits = _limits()
    facts = _facts()
    young = BoostAudience(countries=("BR",), age_min=17, age_max=65)
    assert _rejected(replace(_draft(), audience=young), facts, limits) == ERR_AUDIENCE
    inverted = BoostAudience(countries=("BR",), age_min=40, age_max=30)
    assert _rejected(replace(_draft(), audience=inverted), facts, limits) == (
        ERR_AUDIENCE
    )
    abroad = BoostAudience(countries=("US",), age_min=18, age_max=65)
    assert _rejected(replace(_draft(), audience=abroad), facts, limits) == ERR_COUNTRY
    empty = BoostAudience(countries=(), age_min=18, age_max=65)
    assert _rejected(replace(_draft(), audience=empty), facts, limits) == ERR_COUNTRY


def test_pending_open_and_media_rejections() -> None:
    limits = _limits()
    draft = _draft()
    pending = replace(_facts(), pending_count=limits.max_pending)
    assert _rejected(draft, pending, limits) == ERR_PENDING
    opened = replace(_facts(), open_exists=True)
    assert _rejected(draft, opened, limits) == ERR_OPEN
    missing = replace(
        _facts(),
        media=MediaEligibility(
            posted_at=None, product_type=PRODUCT_STORY, permalink=None
        ),
    )
    assert _rejected(draft, missing, limits) == ERR_MEDIA
    old = _NOW - timedelta(days=limits.max_age_days + 1)
    aged = replace(
        _facts(),
        media=MediaEligibility(
            posted_at=old, product_type=PRODUCT_FEED, permalink=None
        ),
    )
    assert _rejected(draft, aged, limits) == ERR_MEDIA


def test_illegal_transition_and_idempotency_key() -> None:
    with pytest.raises(IllegalBoostTransitionError):
        assert_transition(STATUS_ACTIVE, STATUS_PENDING)
    with pytest.raises(BoostError):
        parse_idempotency_key(None)
    with pytest.raises(BoostError):
        parse_idempotency_key("short")
    with pytest.raises(BoostError):
        parse_idempotency_key("a" * 129)
    assert parse_idempotency_key(_KEY) == _KEY


def _request() -> IgInsightsRequest:
    return IgInsightsRequest(
        since=None,
        until=None,
        limit=IG_INSIGHTS_DEFAULT_LIMIT,
        media_type=None,
        product_type=None,
        refresh=False,
    )


def test_query_window_and_limit() -> None:
    resolved = resolve_query(_request(), _NOW)
    assert resolved.limit == IG_INSIGHTS_DEFAULT_LIMIT
    inverted = replace(_request(), since=_NOW, until=_NOW)
    with pytest.raises(IgInsightsQueryError) as caught:
        resolve_query(inverted, _NOW)
    assert caught.value.code == ERR_WINDOW_INVALID
    assert parse_limit(None) == IG_INSIGHTS_DEFAULT_LIMIT
    assert parse_limit("") == IG_INSIGHTS_DEFAULT_LIMIT
    assert parse_limit(str(IG_INSIGHTS_MAX_LIMIT)) == IG_INSIGHTS_MAX_LIMIT
    with pytest.raises(IgInsightsQueryError):
        parse_limit("nope")
    with pytest.raises(IgInsightsQueryError) as low:
        parse_limit("0")
    assert low.value.code == ERR_LIMIT_INVALID
    with pytest.raises(IgInsightsQueryError):
        parse_limit(str(IG_INSIGHTS_MAX_LIMIT + 1))


def test_timestamps_choices_and_refresh() -> None:
    assert parse_timestamp(None) is None
    assert parse_timestamp("") is None
    naive = parse_timestamp("2026-10-29T18:00:00")
    assert naive is not None
    assert naive.tzinfo is UTC
    aware = parse_timestamp("2026-10-29T18:00:00Z")
    assert aware is not None
    assert aware.tzinfo is not None
    with pytest.raises(IgInsightsQueryError) as bad:
        parse_timestamp("yesterday")
    assert bad.value.code == ERR_TIMESTAMP_INVALID
    assert media_type_or_raise(None) is None
    assert media_type_or_raise("") is None
    assert media_type_or_raise(MEDIA_IMAGE) == MEDIA_IMAGE
    with pytest.raises(IgInsightsQueryError) as media:
        media_type_or_raise("STORY")
    assert media.value.code == ERR_MEDIA_TYPE_INVALID
    assert product_type_or_raise(PRODUCT_FEED) == PRODUCT_FEED
    with pytest.raises(IgInsightsQueryError) as product:
        product_type_or_raise(PRODUCT_STORY)
    assert product.value.code == ERR_PRODUCT_TYPE_INVALID
    assert parse_refresh(None) is False
    assert parse_refresh("") is False
    assert parse_refresh("true") is True
    assert parse_refresh("false") is False
    with pytest.raises(IgInsightsQueryError) as refresh:
        parse_refresh("maybe")
    assert refresh.value.code == ERR_REFRESH_INVALID
    too_old = _NOW - timedelta(days=IG_INSIGHTS_MAX_SINCE_DAYS + 1)
    with pytest.raises(IgInsightsQueryError):
        resolve_query(replace(_request(), since=too_old), _NOW)
