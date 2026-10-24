"""The photos of a Grok Bot image-edit job (contract section 2.4).

``GET /api/v1/image-bridge/jobs/{job_id}/inputs/{index}``: the Grok Bot
fetches each linked photo with ``X-Image-Bridge-Token`` set to the job's
callback token. The photo is the owner's library photo re-encoded on each
request (PNG, metadata stripped, at most 1024 px); nothing is stored. It is
served only while the job is pending and before its deadline; every refusal
is a 404 so neither jobs nor photos can be probed. The response is never
cached. The URL carries no token, and nothing here logs the header.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.modules.editorial.public import cover_generation_input
from rag_backend.modules.image_bridge.public import (
    HEADER_CACHE_CONTROL,
    IMAGE_BRIDGE_TOKEN_HEADER,
    INPUT_CACHE_CONTROL,
    INPUT_MEDIA_TYPE,
    PATH_JOB_INPUT_ROUTE,
    ROUTER_PREFIX,
    JobInputGate,
    JobInputRequest,
    build_job_input_gate,
)

router = APIRouter(prefix=ROUTER_PREFIX, tags=["image-bridge"])

_NOT_FOUND = "not found"
_MAX_INDEX = 9


def get_job_input_gate() -> JobInputGate:
    """FastAPI dependency; tests override it."""
    return build_job_input_gate()


def _job_request(
    job_id: UUID,
    token: Annotated[str, Header(alias=IMAGE_BRIDGE_TOKEN_HEADER)] = "",
) -> JobInputRequest:
    return JobInputRequest(job_id=job_id, token=token)


def _input_deps(
    gate: Annotated[JobInputGate, Depends(get_job_input_gate)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[JobInputGate, AsyncSession]:
    return gate, db


@router.get(
    PATH_JOB_INPUT_ROUTE,
    responses={404: {"description": "Unknown, settled or expired job, or bad token"}},
    include_in_schema=False,
)
async def get_job_input(
    job: Annotated[JobInputRequest, Depends(_job_request)],
    index: int,
    deps: Annotated[tuple[JobInputGate, AsyncSession], Depends(_input_deps)],
) -> Response:
    """The re-encoded photo, or 404."""
    gate, db = deps
    if not 0 <= index <= _MAX_INDEX or not await gate.allows(job):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    photo = await cover_generation_input(db, job.job_id, index)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return Response(
        content=photo,
        media_type=INPUT_MEDIA_TYPE,
        headers={HEADER_CACHE_CONTROL: INPUT_CACHE_CONTROL},
    )


__all__ = ["get_job_input_gate", "router"]
