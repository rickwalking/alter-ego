"""POST /api/v1/image-bridge/jobs/{job_id}/result (AE-0393, contract 2.2).

No JWT and no service key: the per-job one-time token in
``X-Image-Bridge-Token`` authenticates. An unknown job and a bad token get
the same 401 body. Only ``b64_json`` is read; the route never fetches a URL.

202 accepted · 401 bad token/unknown job · 409 not pending · 413 too large ·
422 malformed body or invalid image (the job is marked failed).
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from rag_backend.modules.image_bridge.api.body import (
    BodyTooLargeError,
    declared_too_large,
    read_capped_body,
)
from rag_backend.modules.image_bridge.application.callback import (
    CallbackAuth,
    CallbackOutcome,
    ImageBridgeCallbackService,
)
from rag_backend.modules.image_bridge.bootstrap import build_callback_service
from rag_backend.modules.image_bridge.constants import (
    DETAIL_ACCEPTED,
    DETAIL_INVALID,
    DETAIL_NOT_PENDING,
    DETAIL_TOO_LARGE,
    DETAIL_UNAUTHORIZED,
    HEADER_CALLBACK_TOKEN,
    LOG_CALLBACK_REJECTED,
    PATH_JOB_RESULT,
    RESPONSE_FIELD_DETAIL,
    ROUTER_PREFIX,
    TAG_IMAGE_BRIDGE,
)

logger = structlog.get_logger()

router = APIRouter(prefix=ROUTER_PREFIX, tags=[TAG_IMAGE_BRIDGE])

_OUTCOME_RESPONSES: dict[CallbackOutcome, tuple[int, str]] = {
    CallbackOutcome.ACCEPTED: (status.HTTP_202_ACCEPTED, DETAIL_ACCEPTED),
    CallbackOutcome.NOT_PENDING: (status.HTTP_409_CONFLICT, DETAIL_NOT_PENDING),
    CallbackOutcome.INVALID: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        DETAIL_INVALID,
    ),
}


def get_callback_service() -> ImageBridgeCallbackService:
    """FastAPI dependency; tests override it."""
    return build_callback_service()


@router.post(
    PATH_JOB_RESULT,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": DETAIL_UNAUTHORIZED},
        status.HTTP_409_CONFLICT: {"description": DETAIL_NOT_PENDING},
        status.HTTP_413_CONTENT_TOO_LARGE: {"description": DETAIL_TOO_LARGE},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": DETAIL_INVALID},
    },
)
async def post_image_bridge_result(
    job_id: str,
    request: Request,
    service: Annotated[ImageBridgeCallbackService, Depends(get_callback_service)],
) -> JSONResponse:
    """Record the Grok Bot's ImagesResponse or error body on a pending job."""
    if declared_too_large(request):
        return _answer(status.HTTP_413_CONTENT_TOO_LARGE, DETAIL_TOO_LARGE)
    token = request.headers.get(HEADER_CALLBACK_TOKEN)
    job = await service.authorize(CallbackAuth(job_id=job_id, token=token))
    if job is None:
        logger.warning(LOG_CALLBACK_REJECTED, status=status.HTTP_401_UNAUTHORIZED)
        return _answer(status.HTTP_401_UNAUTHORIZED, DETAIL_UNAUTHORIZED)
    try:
        body = await read_capped_body(request)
    except BodyTooLargeError:
        return _answer(status.HTTP_413_CONTENT_TOO_LARGE, DETAIL_TOO_LARGE)
    outcome = await service.record(job, body)
    return _answer(*_OUTCOME_RESPONSES[outcome])


def _answer(code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=code, content={RESPONSE_FIELD_DETAIL: detail})
