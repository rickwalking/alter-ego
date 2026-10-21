"""The owner's slide-1 hook pick at the outline gate (ADR-0021 D5).

The outline phase stores five hook candidates on outline slide 1; the owner
picks or edits one here. The content phase drafts slide 1 with this hook.
Only carousels on a role contract (Ponto de Vista, Radar IA v4) take a hook.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import ERR_FORBIDDEN, ERR_NOT_AUTHENTICATED
from rag_backend.api.dependencies import require_editor_or_admin
from rag_backend.api.dependencies.carousel_access import (
    get_carousel_project_for_domain_user,
)
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.schemas.carousel_content_mode import (
    HookSelectRequest,
    HookSelectResponse,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.domain.constants.content_mode import ERR_HOOK_NOT_SUPPORTED
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.models import User

router = APIRouter()


@dataclass(frozen=True)
class _HookTarget:
    """The carousel id, the caller and the session that commits the hook."""

    project_id: UUID
    user: User
    session: AsyncSession


def _hook_target(
    project_id: UUID,
    user: Annotated[User, Depends(require_editor_or_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> _HookTarget:
    return _HookTarget(project_id=project_id, user=user, session=session)


@router.put(
    "/{project_id}/hook",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        409: {"description": ERR_HOOK_NOT_SUPPORTED},
    },
)
async def select_hook(
    request: HookSelectRequest,
    target: Annotated[_HookTarget, Depends(_hook_target)],
) -> HookSelectResponse:
    """Store the owner's slide-1 hook (<=60 characters, <=10 words)."""
    project = await get_carousel_project_for_domain_user(
        target.session, target.project_id, target.user
    )
    version = project.presentation_policy_version or DEFAULT_PRESENTATION_POLICY_VERSION
    if not load_presentation_policy(version).has_roles:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ERR_HOOK_NOT_SUPPORTED
        )
    project.hook_text = request.hook_text
    await target.session.commit()
    return HookSelectResponse(project_id=target.project_id, hook_text=request.hook_text)


__all__ = ["router"]
