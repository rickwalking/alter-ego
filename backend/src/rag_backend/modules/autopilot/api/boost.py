"""``/api/autopilot/boost-request`` routes. The key cannot approve or spend."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.rate_limits import (
    RATE_LIMIT_AUTOPILOT,
    RATE_LIMIT_AUTOPILOT_BOOST,
)
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.modules.autopilot.api.auth import require_autopilot_api_key
from rag_backend.modules.autopilot.api.boost_schemas import (
    BoostRequestCreate,
    BoostRequestList,
    BoostRequestResponse,
)
from rag_backend.modules.autopilot.api.dependencies import clock_from
from rag_backend.modules.autopilot.application.boost_requests import (
    BoostDeps,
    BoostRequestService,
    CreateCommand,
)
from rag_backend.modules.autopilot.boost_constants import (
    HEADER_IDEMPOTENCY_KEY,
    LIST_DEFAULT,
    LIST_MAX,
    PATH_BOOST_REQUEST,
    PATH_BOOST_REQUEST_ID,
    PATH_BOOST_REQUESTS,
)
from rag_backend.modules.autopilot.constants import (
    RATE_LIMIT_SCOPE_AUTOPILOT,
    ROUTER_PREFIX,
    TAG_AUTOPILOT,
)
from rag_backend.modules.autopilot.domain.boost import (
    BoostAudience,
    BoostDraft,
    BoostError,
    BoostListQuery,
    BoostRequest,
    parse_idempotency_key,
)
from rag_backend.modules.autopilot.domain.boost_policy import (
    BoostLimits,
    allowed_countries,
)
from rag_backend.modules.autopilot.infrastructure.boost_notifier import (
    TelegramBoostMessenger,
)
from rag_backend.modules.autopilot.infrastructure.boost_store import SqlBoostStore

router = APIRouter(
    prefix=ROUTER_PREFIX,
    tags=[TAG_AUTOPILOT],
    dependencies=[Depends(require_autopilot_api_key)],
)


@dataclass(frozen=True)
class _Bundle:
    service: BoostRequestService
    limits: BoostLimits
    store: SqlBoostStore


async def _bundle(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[_Bundle]:
    store = SqlBoostStore(session)
    await session.connection()
    token = settings.telegram_bot_token.get_secret_value()
    yield _Bundle(
        service=BoostRequestService(
            BoostDeps(
                store=store,
                messenger=TelegramBoostMessenger(
                    token=token, chat_id=settings.telegram_owner_chat_id
                ),
                clock=clock_from(request),
                owner_chat_id=settings.telegram_owner_chat_id,
            )
        ),
        limits=limits_from(settings),
        store=store,
    )


def limits_from(settings: Settings) -> BoostLimits:
    """Caps from the process settings."""
    countries = allowed_countries(settings.boost_allowed_countries)
    return BoostLimits(
        requests_enabled=settings.boost_requests_enabled,
        spend_enabled=settings.boost_enabled,
        max_daily_cents=settings.boost_max_daily_budget_cents,
        min_daily_cents=settings.boost_min_daily_budget_cents,
        max_days=settings.boost_max_days,
        max_week_cents=settings.boost_max_total_cents_per_week,
        max_pending=settings.boost_max_pending,
        max_age_days=settings.boost_max_media_age_days,
        allowed_countries=countries,
        approval_ttl_hours=settings.boost_approval_ttl_hours,
        currency=settings.boost_currency,
        poll_minutes=settings.boost_insights_poll_minutes,
        max_attempts=settings.boost_launch_max_attempts,
    )


@router.post(PATH_BOOST_REQUEST, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(RATE_LIMIT_AUTOPILOT_BOOST)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def post_boost_request(
    request: Request, bundle: Annotated[_Bundle, Depends(_bundle)]
) -> BoostRequestResponse:
    """Create a pending request and message the owner."""
    try:
        payload = await request.json()
        body = BoostRequestCreate.model_validate(payload)
        key = parse_idempotency_key(request.headers.get(HEADER_IDEMPOTENCY_KEY))
        created = await bundle.service.create(
            CreateCommand(draft=_draft(body, key), limits=bundle.limits)
        )
    except BoostError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.code) from None
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None
    return _response(created.request)


@router.get(PATH_BOOST_REQUEST_ID)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def get_boost_request(
    request: Request,
    boost_id: UUID,
    bundle: Annotated[_Bundle, Depends(_bundle)],
) -> BoostRequestResponse:
    """Status from Postgres. This route never calls Meta."""
    del request
    try:
        found = await bundle.service.get(boost_id)
    except BoostError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.code) from None
    return _response(found)


@router.get(PATH_BOOST_REQUESTS)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def list_boost_requests(
    request: Request, bundle: Annotated[_Bundle, Depends(_bundle)]
) -> BoostRequestList:
    """Newest first. ``status`` may be repeated."""
    query = _list_query(request)
    rows = await bundle.store.list_requests(query)
    return BoostRequestList(items=[_response(row) for row in rows])


def _draft(body: BoostRequestCreate, key: str) -> BoostDraft:
    return BoostDraft(
        media_id=body.media_id,
        daily_budget_cents=body.daily_budget_cents,
        days=body.days,
        objective=body.objective,
        audience=BoostAudience(
            countries=tuple(body.audience.countries),
            age_min=body.audience.age_min,
            age_max=body.audience.age_max,
        ),
        reason=body.reason,
        score=body.score,
        start_at=body.start_at,
        idempotency_key=key,
    )


def _response(request: BoostRequest) -> BoostRequestResponse:
    return BoostRequestResponse(
        id=request.id,
        status=request.status,
        media_id=request.media_id,
        permalink=request.permalink,
        objective=request.objective,
        daily_budget_cents=request.daily_budget_cents,
        days=request.days,
        total_budget_cents=request.total_budget_cents,
        currency=request.currency,
        reason=request.reason,
        created_at=request.created_at,
        expires_at=request.expires_at,
        error_code=request.error_code,
        meta_campaign_id=request.meta_campaign_id,
        meta_ad_id=request.meta_ad_id,
    )


def _list_query(request: Request) -> BoostListQuery:
    raw = request.query_params.getlist("status")
    media = request.query_params.get("media_id")
    limit_raw = request.query_params.get("limit")
    limit = LIST_DEFAULT
    if limit_raw is not None and limit_raw.isdigit():
        limit = min(int(limit_raw), LIST_MAX)
    return BoostListQuery(
        statuses=tuple(raw),
        media_id=media,
        limit=limit,
    )
