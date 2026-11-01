"""The exact Marketing API bodies for one boost. Pure: no HTTP, no clock.

The launch and the validate-only check both build their bodies here, so what the
check validates is what the launch sends.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from rag_backend.modules.autopilot.boost_constants import (
    AGE_MAX,
    AGE_MIN,
    BID_LOWEST,
    BILLING_IMPRESSIONS,
    BUYING_AUCTION,
    DEFAULT_MAX_DAYS,
    DESTINATION_ON_POST,
    ERR_AUDIENCE,
    ERR_COUNTRY,
    ERR_DAYS,
    OBJECTIVE_OUTCOME,
    OPTIMIZATION_POST,
    STATUS_PAUSED,
)
from rag_backend.modules.autopilot.domain.boost import BoostAudience, BoostRequest
from rag_backend.modules.autopilot.infrastructure.meta_ads_errors import AdsCallError
from rag_backend.modules.autopilot.infrastructure.meta_graph import AdsConfig
from rag_backend.modules.autopilot.meta_ads_constants import (
    ADVANTAGE_OFF,
    ALLOWED_AD_COUNTRIES,
    ERR_SCHEDULE,
    IG_POSITION_FEED,
    PLATFORM_INSTAGRAM,
    TARGET_ADVANTAGE,
    TARGET_AGE_MAX,
    TARGET_AGE_MIN,
    TARGET_AUTOMATION,
    TARGET_COUNTRIES,
    TARGET_GEO,
    TARGET_IG_POSITIONS,
    TARGET_PLATFORMS,
)


@dataclass(frozen=True, kw_only=True)
class AdsetWindow:
    """When the ad set runs. ``end - start`` is ``days`` and never over the cap."""

    start: datetime
    end: datetime


def adset_window(request: BoostRequest, now: datetime) -> AdsetWindow:
    """Start at the requested time (or now, if that is past) and run ``days`` days."""
    if request.days < 1:
        raise AdsCallError(ERR_SCHEDULE, permanent=True)
    if request.days > DEFAULT_MAX_DAYS:
        raise AdsCallError(ERR_DAYS, permanent=True)
    start = now if request.starts_at is None else max(now, request.starts_at)
    return AdsetWindow(start=start, end=start + timedelta(days=request.days))


def targeting(audience: BoostAudience) -> str:
    """The ad set targeting JSON. An audience outside the caps is refused."""
    countries = sorted(set(audience.countries))
    if not countries or not set(countries) <= ALLOWED_AD_COUNTRIES:
        raise AdsCallError(ERR_COUNTRY, permanent=True)
    if not AGE_MIN <= audience.age_min <= audience.age_max <= AGE_MAX:
        raise AdsCallError(ERR_AUDIENCE, permanent=True)
    spec: dict[str, object] = {
        TARGET_GEO: {TARGET_COUNTRIES: countries},
        TARGET_AGE_MIN: audience.age_min,
        TARGET_AGE_MAX: audience.age_max,
        TARGET_PLATFORMS: [PLATFORM_INSTAGRAM],
        TARGET_IG_POSITIONS: [IG_POSITION_FEED],
        TARGET_AUTOMATION: {TARGET_ADVANTAGE: ADVANTAGE_OFF},
    }
    return json.dumps(spec, separators=(",", ":"), sort_keys=True)


def campaign_payload(request: BoostRequest) -> dict[str, str]:
    """Paused engagement campaign, ad set budgets (no campaign budget sharing)."""
    return {
        "name": f"AE boost {str(request.id)[:8]} {request.media_id}",
        "objective": OBJECTIVE_OUTCOME,
        "status": STATUS_PAUSED,
        "buying_type": BUYING_AUCTION,
        "special_ad_categories": "[]",
        "is_adset_budget_sharing_enabled": "false",
    }


def adset_payload(
    request: BoostRequest, campaign_id: str, window: AdsetWindow
) -> dict[str, str]:
    """Paused ad set: daily budget, capped audience, start and end time."""
    return {
        "name": f"AE boost {str(request.id)[:8]}",
        "campaign_id": campaign_id,
        "status": STATUS_PAUSED,
        "daily_budget": str(request.daily_budget_cents),
        "billing_event": BILLING_IMPRESSIONS,
        "optimization_goal": OPTIMIZATION_POST,
        "bid_strategy": BID_LOWEST,
        "destination_type": DESTINATION_ON_POST,
        "targeting": targeting(request.audience),
        "start_time": str(int(window.start.timestamp())),
        "end_time": str(int(window.end.timestamp())),
    }


def creative_payload(request: BoostRequest, config: AdsConfig) -> dict[str, str]:
    """The existing Instagram post as the creative: Page, Instagram user and media."""
    return {
        "name": f"AE boost {str(request.id)[:8]}",
        "object_id": config.page_id,
        "instagram_user_id": config.ig_user_id,
        "source_instagram_media_id": request.media_id,
    }


def ad_payload(adset_id: str, creative_id: str) -> dict[str, str]:
    """Paused ad joining the ad set and the creative."""
    return {
        "name": f"AE {creative_id}",
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}, separators=(",", ":")),
        "status": STATUS_PAUSED,
    }


__all__ = [
    "AdsetWindow",
    "ad_payload",
    "adset_payload",
    "adset_window",
    "campaign_payload",
    "creative_payload",
    "targeting",
]
