"""The quality rubric a new carousel is created with.

``rubric_id`` left out of the request takes the default carousel rubric (or
none when there is no default); an explicit ``null`` is the presentation policy
alone ("Política padrão"); an id must name a rubric applicable to carousels.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.schemas import CarouselProjectCreate
from rag_backend.domain.constants.carousel_rubric import ERR_RUBRIC_NOT_FOUND
from rag_backend.modules.editorial.public import CarouselRubricAcl, RubricChoiceError

_RUBRIC_FIELD = "rubric_id"


async def create_rubric_id(
    session: AsyncSession, request: CarouselProjectCreate
) -> str | None:
    """The rubric id to store; 404 for an unknown rubric, 422 for a non-carousel one."""
    if _RUBRIC_FIELD in request.model_fields_set and request.rubric_id is None:
        return None
    chosen = str(request.rubric_id) if request.rubric_id is not None else None
    try:
        return await CarouselRubricAcl(session).rubric_for_create(chosen)
    except RubricChoiceError as exc:
        code = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if code == ERR_RUBRIC_NOT_FOUND
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(status_code=status_code, detail=code) from exc


__all__ = ["create_rubric_id"]
