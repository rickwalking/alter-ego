"""Marketing API calls. Created paused, activated last, and never when disabled."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, replace

import httpx

from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN, ENCODING_UTF8
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.autopilot.boost_constants import (
    ACCOUNT_ACTIVE,
    BID_LOWEST,
    BILLING_IMPRESSIONS,
    BUYING_AUCTION,
    DESTINATION_ON_POST,
    ERR_ACCOUNT,
    ERR_ADS_DISABLED,
    ERR_BELOW_META,
    ERR_MEDIA_HIDDEN,
    GRAPH_ADS,
    GRAPH_ADSETS,
    GRAPH_CAMPAIGNS,
    GRAPH_CREATIVES,
    HTTP_ERROR_MIN,
    OBJECTIVE_OUTCOME,
    OPTIMIZATION_POST,
    STATUS_ACTIVE_AD,
    STATUS_PAUSED,
)
from rag_backend.modules.autopilot.domain.boost import BoostRequest

_PROOF = "appsecret_proof"


class AdsCallError(Exception):
    """A classified Marketing API failure. Permanent errors do not retry."""

    def __init__(self, code: str, *, permanent: bool) -> None:
        self.code = code
        self.permanent = permanent
        super().__init__(code)


@dataclass(frozen=True, kw_only=True)
class AdsConfig:
    """System User token and the ad account. ``enabled`` is the kill switch."""

    enabled: bool
    token: str
    app_secret: str
    account_id: str
    page_id: str
    ig_user_id: str
    graph_base: str


class MetaAdsGateway:
    """Paused creates, then activate. A disabled switch performs no HTTP."""

    def __init__(self, config: AdsConfig, client: httpx.AsyncClient) -> None:
        self._config = config
        self._client = client

    async def launch(self, request: BoostRequest) -> BoostRequest:
        """Create the four objects paused, then turn them on."""
        self._require_enabled()
        await self._preflight(request)
        campaign = request.meta_campaign_id or await self._campaign(request)
        adset = request.meta_adset_id or await self._adset(request, campaign)
        creative = request.meta_creative_id or await self._creative(request)
        ad = request.meta_ad_id or await self._ad(request, adset, creative)
        self._require_enabled()
        await self._activate(campaign, adset, ad)
        return replace(
            request,
            meta_campaign_id=campaign,
            meta_adset_id=adset,
            meta_creative_id=creative,
            meta_ad_id=ad,
        )

    async def pause(self, campaign_id: str) -> None:
        """Pause a campaign. No HTTP when the switch is off."""
        if not self._config.enabled:
            return
        await self._post(f"/{campaign_id}", {"status": STATUS_PAUSED})

    def _require_enabled(self) -> None:
        if not self._config.enabled:
            raise AdsCallError(ERR_ADS_DISABLED, permanent=False)

    async def _preflight(self, request: BoostRequest) -> None:
        media = await self._get(f"/{request.media_id}", {"fields": "id"})
        if "id" not in media:
            raise AdsCallError(ERR_MEDIA_HIDDEN, permanent=True)
        account = self._config.account_id
        state = await self._get(f"/act_{account}", {"fields": "account_status"})
        if state.get("account_status") != ACCOUNT_ACTIVE:
            raise AdsCallError(ERR_ACCOUNT, permanent=True)
        floors = await self._get(f"/act_{account}/minimum_budgets", {})
        floor = floors.get("min_daily_budget_high_freq")
        if isinstance(floor, int) and request.daily_budget_cents < floor:
            raise AdsCallError(ERR_BELOW_META, permanent=True)

    async def _campaign(self, request: BoostRequest) -> str:
        payload = {
            "name": f"AE boost {str(request.id)[:8]} {request.media_id}",
            "objective": OBJECTIVE_OUTCOME,
            "status": STATUS_PAUSED,
            "buying_type": BUYING_AUCTION,
            "special_ad_categories": "[]",
            "is_adset_budget_sharing_enabled": "false",
        }
        return await self._created(GRAPH_CAMPAIGNS, payload)

    async def _adset(self, request: BoostRequest, campaign_id: str) -> str:
        payload = {
            "name": f"AE boost {str(request.id)[:8]}",
            "campaign_id": campaign_id,
            "status": STATUS_PAUSED,
            "daily_budget": str(request.daily_budget_cents),
            "billing_event": BILLING_IMPRESSIONS,
            "optimization_goal": OPTIMIZATION_POST,
            "bid_strategy": BID_LOWEST,
            "destination_type": DESTINATION_ON_POST,
        }
        return await self._created(GRAPH_ADSETS, payload)

    async def _creative(self, request: BoostRequest) -> str:
        payload = {
            "name": f"AE boost {str(request.id)[:8]}",
            "object_id": self._config.page_id,
            "instagram_user_id": self._config.ig_user_id,
            "source_instagram_media_id": request.media_id,
        }
        return await self._created(GRAPH_CREATIVES, payload)

    async def _ad(self, request: BoostRequest, adset_id: str, creative_id: str) -> str:
        del request
        payload = {
            "name": f"AE {creative_id}",
            "adset_id": adset_id,
            "creative": f'{{"creative_id":"{creative_id}"}}',
            "status": STATUS_PAUSED,
        }
        return await self._created(GRAPH_ADS, payload)

    async def _activate(self, campaign: str, adset: str, ad: str) -> None:
        for object_id in (campaign, adset, ad):
            self._require_enabled()
            await self._post(f"/{object_id}", {"status": STATUS_ACTIVE_AD})

    async def _created(self, path: str, payload: dict[str, str]) -> str:
        body = await self._post(path, payload)
        created = body.get("id")
        if not isinstance(created, str):
            raise AdsCallError("meta_no_id", permanent=True)
        return created

    async def _get(self, path: str, params: dict[str, str]) -> dict[str, object]:
        response = await self._client.get(self._url(path), params=self._auth(params))
        return _json(response)

    async def _post(self, path: str, payload: dict[str, str]) -> dict[str, object]:
        response = await self._client.post(self._url(path), data=self._auth(payload))
        return _json(response)

    def _url(self, path: str) -> str:
        base = self._config.graph_base.rstrip("/")
        account = self._config.account_id
        return base + path.format(account=account)

    def _auth(self, params: dict[str, str]) -> dict[str, str]:
        signed = dict(params)
        signed[COOKIE_ACCESS_TOKEN] = self._config.token
        secret = self._config.app_secret
        if secret:
            signed[_PROOF] = hmac.new(
                secret.encode(ENCODING_UTF8),
                self._config.token.encode(ENCODING_UTF8),
                hashlib.sha256,
            ).hexdigest()
        return signed


def _json(response: httpx.Response) -> dict[str, object]:
    if response.status_code >= HTTP_ERROR_MIN:
        raise AdsCallError("meta_transient", permanent=False)
    try:
        body = response.json()
    except ValueError as exc:
        raise AdsCallError("meta_transient", permanent=False) from exc
    if not isinstance(body, dict):
        raise AdsCallError("meta_bad_body", permanent=True)
    if response.is_success:
        return body
    error = body.get("error")
    code = error.get("code") if isinstance(error, dict) else response.status_code
    permanent = response.status_code < HTTP_ERROR_MIN
    raise AdsCallError(f"meta_{code}", permanent=permanent)


__all__ = ["AdsCallError", "AdsConfig", "MetaAdsGateway", "SettingsCampaignPauser"]


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
        config = _config(self._settings, token)
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                await MetaAdsGateway(config, client).pause(campaign_id)
            except AdsCallError:
                return False
        return True


def _config(settings: Settings, token: str) -> AdsConfig:
    return AdsConfig(
        enabled=True,
        token=token,
        app_secret=settings.meta_ads_app_secret.get_secret_value().strip(),
        account_id=settings.meta_ad_account_id,
        page_id=settings.meta_page_id,
        ig_user_id=settings.meta_ads_ig_user_id,
        graph_base=settings.meta_ads_graph_base,
    )
