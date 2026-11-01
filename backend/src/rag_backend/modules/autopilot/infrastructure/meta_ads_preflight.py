"""Checks a launch makes before creating anything; the validate-only check reuses them.

Each step is one Graph read and the rule its answer must pass. ``require_page`` needs
no HTTP. The launch stops at the first failing step; the validate-only check reports
every step.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from rag_backend.modules.autopilot.boost_constants import (
    ACCOUNT_ACTIVE,
    ERR_ACCOUNT,
    ERR_BELOW_META,
    ERR_MEDIA_HIDDEN,
    ERR_PAGE_MISSING,
)
from rag_backend.modules.autopilot.domain.boost import BoostRequest
from rag_backend.modules.autopilot.infrastructure.meta_ads_errors import AdsCallError
from rag_backend.modules.autopilot.infrastructure.meta_graph import AdsConfig, GraphCall
from rag_backend.modules.autopilot.meta_ads_constants import (
    CALL_MIN_BUDGETS,
    CALL_PREFLIGHT_ACCOUNT,
    CALL_PREFLIGHT_MEDIA,
    FIELD_CALL,
)

FLOOR_FIELD = "min_daily_budget_high_freq"

Rule = Callable[[dict[str, object]], None]


@dataclass(frozen=True, kw_only=True)
class PreflightStep:
    """One preflight read and the rule its body must pass."""

    call: GraphCall
    rule: Rule


def require_page(config: AdsConfig) -> None:
    """Meta boosts an Instagram post only through a Page and its Instagram user."""
    if config.page_id.strip() == "" or config.ig_user_id.strip() == "":
        raise AdsCallError(ERR_PAGE_MISSING, permanent=True)


def media_check(media_id: str) -> GraphCall:
    """The preflight read of the post. The ads token needs ``instagram_basic``."""
    return GraphCall(
        call=CALL_PREFLIGHT_MEDIA, path=f"/{media_id}", params={"fields": "id"}
    )


def account_check() -> GraphCall:
    """The preflight read of the ad account status."""
    return GraphCall(
        call=CALL_PREFLIGHT_ACCOUNT,
        path="/act_{account}",
        params={"fields": "account_status"},
    )


def budget_floor_check() -> GraphCall:
    """The preflight read of Meta's minimum daily budgets."""
    return GraphCall(
        call=CALL_MIN_BUDGETS, path="/act_{account}/minimum_budgets", params={}
    )


def _fail(code: str, call: str) -> AdsCallError:
    return AdsCallError(code, permanent=True, detail={FIELD_CALL: call})


def _media_visible(body: dict[str, object]) -> None:
    if "id" not in body:
        raise _fail(ERR_MEDIA_HIDDEN, CALL_PREFLIGHT_MEDIA)


def _account_active(body: dict[str, object]) -> None:
    if body.get("account_status") != ACCOUNT_ACTIVE:
        raise _fail(ERR_ACCOUNT, CALL_PREFLIGHT_ACCOUNT)


def _over_floor(daily_cents: int) -> Rule:
    def rule(body: dict[str, object]) -> None:
        floor = body.get(FLOOR_FIELD)
        if isinstance(floor, int) and daily_cents < floor:
            raise _fail(ERR_BELOW_META, CALL_MIN_BUDGETS)

    return rule


def preflight_steps(request: BoostRequest) -> tuple[PreflightStep, ...]:
    """Media visible, account active, daily budget at or over Meta's floor."""
    return (
        PreflightStep(call=media_check(request.media_id), rule=_media_visible),
        PreflightStep(call=account_check(), rule=_account_active),
        PreflightStep(
            call=budget_floor_check(), rule=_over_floor(request.daily_budget_cents)
        ),
    )


__all__ = [
    "PreflightStep",
    "account_check",
    "budget_floor_check",
    "media_check",
    "preflight_steps",
    "require_page",
]
