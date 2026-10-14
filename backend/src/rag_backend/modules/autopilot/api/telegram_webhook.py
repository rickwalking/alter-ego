"""POST /api/telegram/webhook. No JWT and no service API key.

A valid secret always ends in HTTP 200, including duplicates, strangers,
and unknown buttons. A missing or wrong secret is HTTP 401 and does nothing.
"""

from __future__ import annotations

import json
from typing import Annotated, cast

import structlog
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.modules.autopilot.application.owner_actions import OwnerActionService
from rag_backend.modules.autopilot.bootstrap_webhook import (
    OwnerActionBuild,
    build_owner_action_service,
)
from rag_backend.modules.autopilot.domain.webhook_update import (
    parse_webhook_body,
    secrets_match,
)
from rag_backend.modules.autopilot.infrastructure.editorial_driver import EngineFactory
from rag_backend.modules.autopilot.webhook_constants import (
    APP_STATE_ENGINE,
    APP_STATE_OWNER_ACTIONS,
    HEADER_WEBHOOK_AUTH,
    LOG_WEBHOOK_FAILED,
    PATH_TELEGRAM_WEBHOOK,
    TAG_TELEGRAM,
)

logger = structlog.get_logger()

router = APIRouter(tags=[TAG_TELEGRAM])


@router.post(PATH_TELEGRAM_WEBHOOK)
async def post_telegram_webhook(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Accept one Telegram update when the secret header matches."""
    settings = get_settings()
    provided = request.headers.get(HEADER_WEBHOOK_AUTH, "")
    expected = settings.telegram_webhook_secret.get_secret_value()
    if not secrets_match(provided, expected):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    update = parse_webhook_body(_json_body(await request.body()))
    service: OwnerActionService | None = None
    try:
        if update is not None:
            service = _service(request, session)
            await service.handle(update)
        await session.commit()
    except Exception:
        await session.rollback()
        if service is not None:
            service.discard()
        logger.exception(LOG_WEBHOOK_FAILED)
        return Response(status_code=status.HTTP_200_OK)
    # Telegram side effects only after the claim and transitions are durable.
    if service is not None:
        await service.deliver()
    return Response(status_code=status.HTTP_200_OK)


def _service(request: Request, session: AsyncSession) -> OwnerActionService:
    override = getattr(request.app.state, APP_STATE_OWNER_ACTIONS, None)
    if isinstance(override, OwnerActionService):
        return override
    return build_owner_action_service(
        OwnerActionBuild(
            session=session,
            settings=get_settings(),
            engine_factory=_engine_factory(request),
        )
    )


def _engine_factory(request: Request) -> EngineFactory:
    factory = getattr(request.app.state, APP_STATE_ENGINE, None)
    if not callable(factory):
        raise TypeError(LOG_WEBHOOK_FAILED)
    return cast(EngineFactory, factory)


def _json_body(raw: bytes) -> object:
    if not raw:
        return None
    try:
        loaded: object = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return loaded
