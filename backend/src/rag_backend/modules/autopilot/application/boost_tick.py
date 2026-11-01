"""Expire unanswered requests and launch at most one approved boost."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Protocol

import structlog

from rag_backend.modules.autopilot.application.boost_requests import (
    BoostDeps,
    draft_of,
)
from rag_backend.modules.autopilot.boost_constants import (
    ACTOR_WORKER,
    LOG_LAUNCH,
    STATUS_ACTIVE,
    STATUS_APPROVED,
    STATUS_EXPIRED,
    STATUS_FAILED,
    STATUS_LAUNCHING,
    STATUS_PENDING,
    WEEK_DAYS,
)
from rag_backend.modules.autopilot.domain.boost import (
    BoostError,
    BoostListQuery,
    BoostRequest,
    BoostStore,
    StatusSave,
)
from rag_backend.modules.autopilot.domain.boost_policy import BoostLimits, check_launch
from rag_backend.modules.autopilot.infrastructure.meta_ads_gateway import AdsCallError

_SCAN = 20

logger = structlog.get_logger(__name__)


class _Ads(Protocol):
    async def launch(self, request: BoostRequest) -> BoostRequest: ...

    async def pause(self, campaign_id: str) -> None: ...


@dataclass(frozen=True, kw_only=True)
class BoostTickDeps:
    """Store, caps, clock and the ads gateway (None while spending is off)."""

    boosts: BoostDeps
    limits: BoostLimits
    ads: _Ads | None


class BoostTick:
    """One worker pass. A disabled spend switch makes zero ads calls."""

    def __init__(self, deps: BoostTickDeps) -> None:
        self._deps = deps

    async def run(self) -> int:
        """Expire, pause stopped campaigns, and launch at most one."""
        expired = await self._expire()
        if not self._deps.limits.spend_enabled or self._deps.ads is None:
            return expired
        return expired + await self._launch()

    async def _expire(self) -> int:
        now = self._deps.boosts.clock.now()
        rows = await self._deps.boosts.store.list_requests(
            BoostListQuery(statuses=(STATUS_PENDING,), media_id=None, limit=_SCAN)
        )
        count = 0
        for row in rows:
            if row.expires_at >= now:
                continue
            updated = replace(row, status=STATUS_EXPIRED, decided_at=now)
            await self._deps.boosts.store.save_status(
                StatusSave(previous=STATUS_PENDING, request=updated, actor=ACTOR_WORKER)
            )
            count += 1
        if count:
            await self._deps.boosts.store.commit()
        return count

    async def _launch(self) -> int:
        ads = self._deps.ads
        if ads is None:
            return 0
        rows = await self._deps.boosts.store.list_requests(
            BoostListQuery(statuses=(STATUS_APPROVED,), media_id=None, limit=1)
        )
        if not rows:
            return 0
        current = rows[0]
        refused = await self._caps_refusal(current)
        if refused is not None:
            failed = replace(current, status=STATUS_FAILED, error_code=refused)
            await self._finish(STATUS_APPROVED, failed)
            return 1
        launching = replace(current, status=STATUS_LAUNCHING)
        await self._deps.boosts.store.save_status(
            StatusSave(previous=STATUS_APPROVED, request=launching, actor=ACTOR_WORKER)
        )
        await self._finish(STATUS_LAUNCHING, await _attempt(ads, launching))
        return 1

    async def _caps_refusal(self, request: BoostRequest) -> str | None:
        """The cap code when the current caps no longer allow the approved request."""
        at = CapsAt(limits=self._deps.limits, now=self._deps.boosts.clock.now())
        return await caps_refusal(self._deps.boosts.store, request, at)

    async def _finish(self, previous: str, request: BoostRequest) -> None:
        await self._deps.boosts.store.save_status(
            StatusSave(previous=previous, request=request, actor=ACTOR_WORKER)
        )
        await self._deps.boosts.store.commit()


@dataclass(frozen=True, kw_only=True)
class CapsAt:
    """The caps in force and the time the rolling week ends."""

    limits: BoostLimits
    now: datetime


async def caps_refusal(
    store: BoostStore, request: BoostRequest, at: CapsAt
) -> str | None:
    """The cap code when the caps in force no longer allow the request, else None.

    The request's own budget is taken out of the weekly total it is checked against.
    """
    since = at.now - timedelta(days=WEEK_DAYS)
    others = max(0, await store.committed_cents(since) - request.total_budget_cents)
    try:
        check_launch(draft_of(request), at.limits, others)
    except BoostError as exc:
        return exc.code
    return None


async def _attempt(ads: _Ads, launching: BoostRequest) -> BoostRequest:
    """The launched request as active, or as failed with Meta's error details."""
    try:
        launched = await ads.launch(launching)
    except AdsCallError as exc:
        _log_failure(launching, exc)
        return replace(
            launching,
            status=STATUS_FAILED,
            error_code=exc.code,
            error_detail=exc.detail,
        )
    return replace(launched, status=STATUS_ACTIVE)


def _log_failure(request: BoostRequest, exc: AdsCallError) -> None:
    """One structured line with Meta's error fields. They never hold the token."""
    logger.warning(
        LOG_LAUNCH,
        request_id=str(request.id),
        error_code=exc.code,
        permanent=exc.permanent,
        meta=exc.detail,
    )


__all__ = ["BoostTick", "BoostTickDeps", "CapsAt", "caps_refusal"]
