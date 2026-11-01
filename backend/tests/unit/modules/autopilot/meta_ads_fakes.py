"""A fake Graph API on ``httpx.MockTransport`` and a stored boost request. No Meta calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl
from uuid import UUID

import httpx

from rag_backend.modules.autopilot.boost_constants import STATUS_APPROVED
from rag_backend.modules.autopilot.domain.boost import BoostAudience, BoostRequest
from rag_backend.modules.autopilot.infrastructure.meta_ads_gateway import (
    AdsConfig,
    MetaAdsGateway,
)

NOW = datetime(2026, 11, 1, 12, tzinfo=UTC)
TOKEN = "ads-token-secret-value"
APP_SECRET = "app-secret"
ACCOUNT = "987"
PAGE = "1122334455"
IG_USER = "17841400000000000"
MEDIA = "18034567890123456"
REQUEST_ID = UUID("0c9a1f0e-5b7e-4a43-9d0e-3f1f6f0d7a11")

_POST_CALLS = {
    "/act_987/campaigns": "campaign",
    "/act_987/adsets": "adset",
    "/act_987/adcreatives": "creative",
    "/act_987/ads": "ad",
}


def config(*, enabled: bool = True) -> AdsConfig:
    """Ads config with a Page and Instagram user."""
    return AdsConfig(
        enabled=enabled,
        token=TOKEN,
        app_secret=APP_SECRET,
        account_id=ACCOUNT,
        page_id=PAGE,
        ig_user_id=IG_USER,
        graph_base="https://graph.example/v23.0",
    )


def request(
    *,
    audience: BoostAudience | None = None,
    days: int = 3,
    starts_at: datetime | None = None,
) -> BoostRequest:
    """An approved request, Brazil 18-65 unless told otherwise."""
    return BoostRequest(
        id=REQUEST_ID,
        idempotency_key="media-20261101",
        request_hash="hash",
        media_id=MEDIA,
        status=STATUS_APPROVED,
        objective="engagement",
        daily_budget_cents=2000,
        days=days,
        total_budget_cents=2000 * days,
        currency="BRL",
        audience=audience or BoostAudience(countries=("BR",), age_min=18, age_max=65),
        reason="Alcance acima da mediana da conta",
        score=1.6,
        created_at=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(hours=11),
        starts_at=starts_at,
    )


def meta_error(
    code: int, subcode: int | None = None, message: str = "Invalid"
) -> httpx.Response:
    """A Graph error body as Meta sends it on a 400."""
    error: dict[str, object] = {
        "message": message,
        "type": "OAuthException",
        "code": code,
        "error_user_title": "Ads creative post was created by an app that is in development mode",
        "error_user_msg": "It must be in public to create this ad.",
        "fbtrace_id": "AbCdEf123",
    }
    if subcode is not None:
        error["error_subcode"] = subcode
    return httpx.Response(400, json={"error": error})


@dataclass(frozen=True)
class Sent:
    """One request the fake received: call name, method and its decoded fields."""

    call: str
    method: str
    fields: dict[str, str]
    url: str


@dataclass
class Graph:
    """Answers success for every call unless ``fail`` names it."""

    fail: dict[str, httpx.Response] = field(default_factory=dict)
    sent: list[Sent] = field(default_factory=list)

    def handle(self, req: httpx.Request) -> httpx.Response:
        """Record the request, then answer it."""
        call = _call_of(req)
        fields = dict(req.url.params) if req.method == "GET" else _form(req)
        self.sent.append(
            Sent(call=call, method=req.method, fields=fields, url=str(req.url))
        )
        if call in self.fail:
            return self.fail[call]
        return _ok(call, len(self.sent))

    def calls(self) -> list[str]:
        """The call names in order."""
        return [item.call for item in self.sent]

    def body(self, call: str) -> dict[str, str]:
        """The fields of the first request for ``call``."""
        return next(item.fields for item in self.sent if item.call == call)

    def client(self) -> httpx.AsyncClient:
        """A client wired to this fake."""
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handle))


def gateway(graph: Graph, ads: AdsConfig | None = None) -> MetaAdsGateway:
    """The real gateway on the fake Graph, with the fixed clock."""
    return MetaAdsGateway(ads or config(), graph.client(), lambda: NOW)


def _form(req: httpx.Request) -> dict[str, str]:
    return dict(parse_qsl(req.content.decode()))


def _call_of(req: httpx.Request) -> str:
    path = req.url.path.removeprefix("/v23.0")
    if req.method == "POST":
        return _POST_CALLS.get(path, "activate")
    if path.endswith("/minimum_budgets"):
        return "min_budgets"
    if path == f"/act_{ACCOUNT}":
        return "preflight_account"
    return "preflight_media"


def _ok(call: str, count: int) -> httpx.Response:
    answers: dict[str, dict[str, object]] = {
        "min_budgets": {"min_daily_budget_high_freq": 100},
        "preflight_account": {"account_status": 1},
        "preflight_media": {"id": MEDIA},
        "activate": {"success": True},
    }
    return httpx.Response(200, json=answers.get(call, {"id": f"id-{call}-{count}"}))
