"""Signed Graph API reads and writes for the ads token, shared by launch and checks."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

import httpx

from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN, ENCODING_UTF8
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.autopilot.infrastructure.meta_ads_errors import (
    CallContext,
    read_body,
)

PROOF_PARAM = "appsecret_proof"


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


@dataclass(frozen=True, kw_only=True)
class GraphCall:
    """One Graph request: its call name, the path and the unsigned parameters."""

    call: str
    path: str
    params: dict[str, str]


class GraphCaller:
    """Adds the token and proof, and turns any failure into an ``AdsCallError``."""

    def __init__(self, config: AdsConfig, client: httpx.AsyncClient) -> None:
        self._config = config
        self._client = client

    async def get(self, call: GraphCall) -> dict[str, object]:
        """A signed GET."""
        response = await self._client.get(
            self._url(call.path), params=self._auth(call.params)
        )
        return read_body(response, self._context(call))

    async def post(self, call: GraphCall) -> dict[str, object]:
        """A signed form POST."""
        response = await self._client.post(
            self._url(call.path), data=self._auth(call.params)
        )
        return read_body(response, self._context(call))

    def _context(self, call: GraphCall) -> CallContext:
        proof = self._proof()
        return CallContext(call=call.call, secrets=(self._config.token, proof))

    def _url(self, path: str) -> str:
        base = self._config.graph_base.rstrip("/")
        return base + path.format(account=self._config.account_id)

    def _auth(self, params: dict[str, str]) -> dict[str, str]:
        signed = dict(params)
        signed[COOKIE_ACCESS_TOKEN] = self._config.token
        proof = self._proof()
        if proof:
            signed[PROOF_PARAM] = proof
        return signed

    def _proof(self) -> str:
        secret = self._config.app_secret
        if not secret:
            return ""
        return hmac.new(
            secret.encode(ENCODING_UTF8),
            self._config.token.encode(ENCODING_UTF8),
            hashlib.sha256,
        ).hexdigest()


def ads_config(settings: Settings, token: str) -> AdsConfig:
    """The enabled ads config from the process settings and a non-empty token."""
    return AdsConfig(
        enabled=True,
        token=token,
        app_secret=settings.meta_ads_app_secret.get_secret_value().strip(),
        account_id=settings.meta_ad_account_id,
        page_id=settings.meta_page_id,
        ig_user_id=settings.meta_ads_ig_user_id,
        graph_base=settings.meta_ads_graph_base,
    )


__all__ = ["PROOF_PARAM", "AdsConfig", "GraphCall", "GraphCaller", "ads_config"]
