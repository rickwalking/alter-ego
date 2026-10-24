"""``POST /carousels/cover-prompt-ideas``: "Mais ideias" for a new cover photo.

Thin HTTP adapter over :class:`CoverPromptIdeasService`. Editors (who create
carousels) get three to six prompt ideas tailored to the topic and palette;
nothing is stored. The paid fast-queue call is rate limited per user. Mounted
before the CRUD router so the path is never read as a ``/{project_id}``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from rag_backend.api.constants import ERR_FORBIDDEN, ERR_NOT_AUTHENTICATED
from rag_backend.api.dependencies import require_editor_or_admin
from rag_backend.api.dependencies.cover_prompt_ideas import (
    get_cover_prompt_ideas_service,
)
from rag_backend.api.middleware.rate_limiting import limiter, user_or_address_key
from rag_backend.api.schemas.carousel_cover_prompt_ideas import (
    CoverIdeasPaletteRequest,
    CoverPromptIdeasRequest,
    CoverPromptIdeasResponse,
)
from rag_backend.application.services.carousel.cover_prompt_ideas_service import (
    CoverIdeasPalette,
    CoverIdeasRequest,
    CoverPromptIdeasError,
    CoverPromptIdeasService,
)
from rag_backend.domain.constants.cover_prompt_ideas import (
    ERR_COVER_PROMPT_IDEAS_UNAVAILABLE,
)
from rag_backend.domain.constants.rate_limits import (
    RATE_LIMIT_COVER_PROMPT_IDEAS,
    RATE_LIMIT_USER_STATE,
)
from rag_backend.domain.models import User

router = APIRouter(tags=["carousels-cover-prompt-ideas"])


@dataclass(frozen=True)
class CoverIdeasCtx:
    """The caller and the ideas service of ``POST /cover-prompt-ideas``."""

    user: User
    service: CoverPromptIdeasService


def get_cover_ideas_ctx(
    request: Request,
    user: Annotated[User, Depends(require_editor_or_admin)],
    service: Annotated[
        CoverPromptIdeasService, Depends(get_cover_prompt_ideas_service)
    ],
) -> CoverIdeasCtx:
    """Resolve the editor and the service; the rate limit keys on the user."""
    setattr(request.state, RATE_LIMIT_USER_STATE, str(user.id))
    return CoverIdeasCtx(user=user, service=service)


def _palette(body: CoverIdeasPaletteRequest | None) -> CoverIdeasPalette | None:
    """The validated request palette as the service's value object."""
    if body is None:
        return None
    return CoverIdeasPalette(
        name=body.name,
        mode=body.mode,
        background=body.background,
        primary=body.primary,
        accent=body.accent,
    )


@router.post(
    "/cover-prompt-ideas",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        503: {"description": ERR_COVER_PROMPT_IDEAS_UNAVAILABLE},
    },
)
@limiter.limit(RATE_LIMIT_COVER_PROMPT_IDEAS, key_func=user_or_address_key)
async def suggest_cover_prompt_ideas(
    request: Request,
    body: CoverPromptIdeasRequest,
    ctx: Annotated[CoverIdeasCtx, Depends(get_cover_ideas_ctx)],
) -> CoverPromptIdeasResponse:
    """Three to six prompt ideas for a new cover photo; nothing is stored."""
    try:
        ideas = await ctx.service.suggest(
            CoverIdeasRequest(
                topic=body.topic,
                palette=_palette(body.palette),
                locale=body.locale,
                user_id=str(ctx.user.id),
            )
        )
    except CoverPromptIdeasError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.code
        ) from exc
    return CoverPromptIdeasResponse(ideas=ideas)


__all__ = ["router"]
