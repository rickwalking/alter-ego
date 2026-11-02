"""Caps for a boost request. Pure. Re-run at approval and at launch."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from rag_backend.modules.autopilot.boost_constants import (
    AGE_MAX,
    AGE_MIN,
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
    ERR_WEEK,
    HTTP_CONFLICT,
    HTTP_TOO_MANY,
    HTTP_UNAVAILABLE,
    HTTP_UNPROCESSABLE,
    OBJECTIVE_ENGAGEMENT,
)
from rag_backend.modules.autopilot.domain.boost import (
    BoostDraft,
    BoostError,
    MediaEligibility,
)
from rag_backend.modules.autopilot.ig_media_constants import PRODUCT_FEED, PRODUCT_REELS

_PRODUCTS = frozenset({PRODUCT_FEED, PRODUCT_REELS})


@dataclass(frozen=True, kw_only=True)
class BoostLimits:
    """The env caps. ``enabled`` is the spend switch, not the request switch."""

    requests_enabled: bool
    spend_enabled: bool
    max_daily_cents: int
    min_daily_cents: int
    max_days: int
    max_week_cents: int
    max_pending: int
    max_age_days: int
    allowed_countries: frozenset[str]
    approval_ttl_hours: int
    currency: str
    poll_minutes: int
    max_attempts: int


@dataclass(frozen=True, kw_only=True)
class PolicyFacts:
    """Live totals the policy cannot know by itself."""

    now: datetime
    committed_cents: int
    pending_count: int
    media: MediaEligibility
    open_exists: bool


def check_request(draft: BoostDraft, limits: BoostLimits, facts: PolicyFacts) -> None:
    """Raise ``BoostError`` when the draft is not allowed. Store nothing."""
    if not limits.requests_enabled:
        raise BoostError(ERR_DISABLED, HTTP_UNAVAILABLE)
    _shape(draft, limits)
    _budget(draft, limits, facts)
    _media(draft, limits, facts)


def check_launch(draft: BoostDraft, limits: BoostLimits, committed_cents: int) -> None:
    """Re-run the shape and weekly caps right before spending.

    ``committed_cents`` excludes the request itself, so a cap lowered after the
    approval still binds. Raises ``BoostError`` with the same codes as the request.
    """
    _shape(draft, limits)
    if committed_cents + draft.daily_budget_cents * draft.days > limits.max_week_cents:
        raise BoostError(ERR_WEEK, HTTP_UNPROCESSABLE)


def allowed_countries(raw: str) -> frozenset[str]:
    """The comma-separated ``BOOST_ALLOWED_COUNTRIES`` value as a set."""
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def _shape(draft: BoostDraft, limits: BoostLimits) -> None:
    if draft.objective != OBJECTIVE_ENGAGEMENT:
        raise BoostError(ERR_OBJECTIVE, HTTP_UNPROCESSABLE)
    if draft.daily_budget_cents > limits.max_daily_cents:
        raise BoostError(ERR_DAILY_OVER, HTTP_UNPROCESSABLE)
    if draft.daily_budget_cents < limits.min_daily_cents:
        raise BoostError(ERR_DAILY_UNDER, HTTP_UNPROCESSABLE)
    if draft.days > limits.max_days:
        raise BoostError(ERR_DAYS, HTTP_UNPROCESSABLE)
    _audience(draft, limits)


def _audience(draft: BoostDraft, limits: BoostLimits) -> None:
    audience = draft.audience
    if audience.age_min < AGE_MIN or audience.age_max > AGE_MAX:
        raise BoostError(ERR_AUDIENCE, HTTP_UNPROCESSABLE)
    if audience.age_min > audience.age_max:
        raise BoostError(ERR_AUDIENCE, HTTP_UNPROCESSABLE)
    allowed = limits.allowed_countries
    if any(country not in allowed for country in audience.countries):
        raise BoostError(ERR_COUNTRY, HTTP_UNPROCESSABLE)
    if not audience.countries:
        raise BoostError(ERR_COUNTRY, HTTP_UNPROCESSABLE)


def _budget(draft: BoostDraft, limits: BoostLimits, facts: PolicyFacts) -> None:
    total = draft.daily_budget_cents * draft.days
    if facts.committed_cents + total > limits.max_week_cents:
        raise BoostError(ERR_WEEK, HTTP_UNPROCESSABLE)
    if facts.pending_count >= limits.max_pending:
        raise BoostError(ERR_PENDING, HTTP_TOO_MANY)
    if facts.open_exists:
        raise BoostError(ERR_OPEN, HTTP_CONFLICT)


def _media(draft: BoostDraft, limits: BoostLimits, facts: PolicyFacts) -> None:
    posted = facts.media.posted_at
    product = facts.media.product_type
    if posted is None or product not in _PRODUCTS:
        raise BoostError(ERR_MEDIA, HTTP_UNPROCESSABLE)
    oldest = facts.now - timedelta(days=limits.max_age_days)
    if posted < oldest:
        raise BoostError(ERR_MEDIA, HTTP_UNPROCESSABLE)
    del draft


__all__ = [
    "BoostLimits",
    "PolicyFacts",
    "allowed_countries",
    "check_launch",
    "check_request",
]
