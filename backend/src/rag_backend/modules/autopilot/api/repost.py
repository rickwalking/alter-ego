"""``/api/autopilot/repost`` and ``/reposts``. The key can create and read drafts,
never approve them; approval is the owner's Telegram tap (ADR-0031).

Errors answer ``{"error": {"code", "message", "field"}}``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AUTOPILOT
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.modules.autopilot.api.auth import require_autopilot_api_key
from rag_backend.modules.autopilot.api.repost_mapping import (
    accepted,
    draft_from,
    error_response,
    invalid_body,
    repost_view,
)
from rag_backend.modules.autopilot.api.repost_schemas import (
    RepostAccepted,
    RepostCreate,
    RepostListView,
    RepostView,
)
from rag_backend.modules.autopilot.application.repost_drafts import RepostDraftService
from rag_backend.modules.autopilot.bootstrap_repost import repost_draft_service
from rag_backend.modules.autopilot.constants import (
    RATE_LIMIT_SCOPE_AUTOPILOT,
    ROUTER_PREFIX,
    TAG_AUTOPILOT,
)
from rag_backend.modules.autopilot.domain.repost import (
    RepostError,
    RepostListQuery,
    invalid,
    parse_idempotency_key,
)
from rag_backend.modules.autopilot.reels_constants import REELS_HTTP_TIMEOUT_SECONDS
from rag_backend.modules.autopilot.repost_constants import (
    ALL_STATUSES,
    FIELD_BODY,
    FIELD_LIMIT,
    FIELD_SINCE,
    FIELD_STATUS,
    HEADER_IDEMPOTENCY_KEY,
    LIST_DEFAULT,
    LIST_MAX,
    PATH_REPOST,
    PATH_REPOST_ID,
    PATH_REPOSTS,
)

router = APIRouter(
    prefix=ROUTER_PREFIX,
    tags=[TAG_AUTOPILOT],
    dependencies=[Depends(require_autopilot_api_key)],
)


@dataclass(frozen=True, kw_only=True)
class RepostBundle:
    """The draft service and the site origin of the preview URLs."""

    service: RepostDraftService
    base: str


async def repost_bundle(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[RepostBundle]:
    """The draft service for one request."""
    async with httpx.AsyncClient(timeout=REELS_HTTP_TIMEOUT_SECONDS) as client:
        yield RepostBundle(
            service=repost_draft_service(session, settings, client),
            base=settings.carousel_public_base_url,
        )


@router.post(
    PATH_REPOST, status_code=status.HTTP_202_ACCEPTED, response_model=RepostAccepted
)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def post_repost(
    request: Request, bundle: Annotated[RepostBundle, Depends(repost_bundle)]
) -> JSONResponse:
    """Store a pending draft. The worker renders it and asks the owner."""
    try:
        key = parse_idempotency_key(request.headers.get(HEADER_IDEMPOTENCY_KEY))
        body = await _body(request)
        repost = await bundle.service.create(draft_from(body, key))
    except RepostError as exc:
        return error_response(exc)
    payload = accepted(repost, bundle.base).model_dump(mode="json")
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=payload)


@router.get(PATH_REPOST_ID, response_model=RepostView)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def get_repost(
    request: Request,
    repost_id: UUID,
    bundle: Annotated[RepostBundle, Depends(repost_bundle)],
) -> JSONResponse:
    """One draft's status, from Postgres only."""
    del request
    try:
        repost = await bundle.service.get(repost_id)
    except RepostError as exc:
        return error_response(exc)
    view = repost_view(repost, bundle.base)
    return JSONResponse(content=view.model_dump(mode="json"))


@router.get(PATH_REPOSTS, response_model=RepostListView)
@limiter.shared_limit(RATE_LIMIT_AUTOPILOT, RATE_LIMIT_SCOPE_AUTOPILOT)
async def list_reposts(
    request: Request, bundle: Annotated[RepostBundle, Depends(repost_bundle)]
) -> JSONResponse:
    """Newest first; ``status`` may repeat; ``since`` is ISO 8601."""
    try:
        query = list_query(request)
    except RepostError as exc:
        return error_response(exc)
    rows = await bundle.service.list(query)
    body = RepostListView(items=[repost_view(row, bundle.base) for row in rows])
    return JSONResponse(content=body.model_dump(mode="json"))


async def _body(request: Request) -> RepostCreate:
    try:
        payload: object = await request.json()
    except ValueError:
        raise invalid(FIELD_BODY, "invalid JSON body") from None
    try:
        return RepostCreate.model_validate(payload)
    except ValidationError as exc:
        raise invalid_body(exc) from None


def list_query(request: Request) -> RepostListQuery:
    """``status`` (repeatable), ``since`` and ``limit``; 400 on a bad value."""
    statuses = tuple(request.query_params.getlist(FIELD_STATUS))
    if any(value not in ALL_STATUSES for value in statuses):
        raise invalid(FIELD_STATUS, "unknown status")
    return RepostListQuery(
        statuses=statuses,
        since=_since(request.query_params.get(FIELD_SINCE)),
        limit=_limit(request.query_params.get(FIELD_LIMIT)),
    )


def _since(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise invalid(FIELD_SINCE, "ISO 8601 timestamp") from None
    if parsed.tzinfo is None:
        raise invalid(FIELD_SINCE, "ISO 8601 with a timezone")
    return parsed


def _limit(raw: str | None) -> int:
    if raw is None:
        return LIST_DEFAULT
    if not raw.isdigit() or not 1 <= int(raw) <= LIST_MAX:
        raise invalid(FIELD_LIMIT, "1-100")
    return int(raw)


__all__ = ["RepostBundle", "list_query", "repost_bundle", "router"]
