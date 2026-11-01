"""Marketing API calls. Created paused, activated last, and never when disabled."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

import httpx

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.autopilot.boost_constants import (
    ACCOUNT_ACTIVE,
    ERR_ACCOUNT,
    ERR_ADS_DISABLED,
    ERR_BELOW_META,
    ERR_MEDIA_HIDDEN,
    ERR_PAGE_MISSING,
    GRAPH_ADS,
    GRAPH_ADSETS,
    GRAPH_CAMPAIGNS,
    GRAPH_CREATIVES,
    STATUS_ACTIVE_AD,
    STATUS_PAUSED,
)
from rag_backend.modules.autopilot.domain.boost import BoostRequest
from rag_backend.modules.autopilot.infrastructure.meta_ads_errors import AdsCallError
from rag_backend.modules.autopilot.infrastructure.meta_ads_payloads import (
    AdsetWindow,
    ad_payload,
    adset_payload,
    adset_window,
    campaign_payload,
    creative_payload,
    targeting,
)
from rag_backend.modules.autopilot.infrastructure.meta_graph import (
    AdsConfig,
    GraphCall,
    GraphCaller,
    ads_config,
)
from rag_backend.modules.autopilot.meta_ads_constants import (
    CALL_ACTIVATE,
    CALL_AD,
    CALL_ADSET,
    CALL_CAMPAIGN,
    CALL_CREATIVE,
    CALL_MIN_BUDGETS,
    CALL_PAUSE,
    CALL_PREFLIGHT_ACCOUNT,
    CALL_PREFLIGHT_MEDIA,
    ERR_META_NO_ID,
    FIELD_CALL,
)

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


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


class MetaAdsGateway:
    """Paused creates, then activate. A disabled switch performs no HTTP."""

    def __init__(
        self, config: AdsConfig, client: httpx.AsyncClient, clock: Clock = _utc_now
    ) -> None:
        self._config = config
        self._graph = GraphCaller(config, client)
        self._clock = clock

    async def launch(self, request: BoostRequest) -> BoostRequest:
        """Check the caps, create the four objects paused, then turn them on.

        An audience or a run length outside the caps fails before any HTTP.
        """
        self._require_enabled()
        self._require_page()
        window = adset_window(request, self._clock())
        targeting(request.audience)
        await self._preflight(request)
        campaign = request.meta_campaign_id or await self._campaign(request)
        adset = request.meta_adset_id or await self._adset(request, campaign, window)
        creative = request.meta_creative_id or await self._creative(request)
        ad = request.meta_ad_id or await self._ad(adset, creative)
        self._require_enabled()
        await self._activate(campaign, adset, ad)
        return replace(
            request,
            meta_campaign_id=campaign,
            meta_adset_id=adset,
            meta_creative_id=creative,
            meta_ad_id=ad,
            starts_at=request.starts_at if request.meta_adset_id else window.start,
            ends_at=request.ends_at if request.meta_adset_id else window.end,
        )

    async def pause(self, campaign_id: str) -> None:
        """Pause a campaign. No HTTP when the switch is off."""
        if not self._config.enabled:
            return
        await self._graph.post(
            GraphCall(
                call=CALL_PAUSE,
                path=f"/{campaign_id}",
                params={"status": STATUS_PAUSED},
            )
        )

    def _require_enabled(self) -> None:
        if not self._config.enabled:
            raise AdsCallError(ERR_ADS_DISABLED, permanent=False)

    def _require_page(self) -> None:
        """Meta boosts an Instagram post only through a Page and its Instagram user."""
        config = self._config
        if config.page_id.strip() == "" or config.ig_user_id.strip() == "":
            raise AdsCallError(ERR_PAGE_MISSING, permanent=True)

    async def _preflight(self, request: BoostRequest) -> None:
        media = await self._graph.get(media_check(request.media_id))
        if "id" not in media:
            raise AdsCallError(ERR_MEDIA_HIDDEN, permanent=True)
        state = await self._graph.get(account_check())
        if state.get("account_status") != ACCOUNT_ACTIVE:
            raise AdsCallError(ERR_ACCOUNT, permanent=True)
        floors = await self._graph.get(budget_floor_check())
        floor = floors.get("min_daily_budget_high_freq")
        if isinstance(floor, int) and request.daily_budget_cents < floor:
            raise AdsCallError(ERR_BELOW_META, permanent=True)

    async def _campaign(self, request: BoostRequest) -> str:
        payload = campaign_payload(request)
        return await self._created(
            GraphCall(call=CALL_CAMPAIGN, path=GRAPH_CAMPAIGNS, params=payload)
        )

    async def _adset(
        self, request: BoostRequest, campaign_id: str, window: AdsetWindow
    ) -> str:
        payload = adset_payload(request, campaign_id, window)
        return await self._created(
            GraphCall(call=CALL_ADSET, path=GRAPH_ADSETS, params=payload)
        )

    async def _creative(self, request: BoostRequest) -> str:
        payload = creative_payload(request, self._config)
        return await self._created(
            GraphCall(call=CALL_CREATIVE, path=GRAPH_CREATIVES, params=payload)
        )

    async def _ad(self, adset_id: str, creative_id: str) -> str:
        payload = ad_payload(adset_id, creative_id)
        return await self._created(
            GraphCall(call=CALL_AD, path=GRAPH_ADS, params=payload)
        )

    async def _activate(self, campaign: str, adset: str, ad: str) -> None:
        for object_id in (campaign, adset, ad):
            self._require_enabled()
            await self._graph.post(
                GraphCall(
                    call=CALL_ACTIVATE,
                    path=f"/{object_id}",
                    params={"status": STATUS_ACTIVE_AD},
                )
            )

    async def _created(self, call: GraphCall) -> str:
        body = await self._graph.post(call)
        created = body.get("id")
        if not isinstance(created, str):
            raise AdsCallError(
                ERR_META_NO_ID, permanent=True, detail={FIELD_CALL: call.call}
            )
        return created


__all__ = [
    "AdsCallError",
    "AdsConfig",
    "MetaAdsGateway",
    "SettingsCampaignPauser",
    "account_check",
    "budget_floor_check",
    "media_check",
]


_TIMEOUT = 20.0


class SettingsCampaignPauser:
    """Pauses one campaign with the ads token. No token means it did not pause."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def pause(self, campaign_id: str) -> bool:
        """True when Meta accepted the pause."""
        token = self._settings.meta_ads_access_token.get_secret_value().strip()
        if token == "":
            return False
        config = ads_config(self._settings, token)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                await MetaAdsGateway(config, client).pause(campaign_id)
            except AdsCallError:
                return False
        return True
