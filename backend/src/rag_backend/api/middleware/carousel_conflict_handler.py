"""Handler mapping CarouselConflictError to an additive 409 body (AE-0316).

``detail`` keeps the legacy machine-readable string (existing clients
string-compare it); ``conflict`` carries the structured payload for new
consumers (AE-0311/0313/0315).
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from rag_backend.api.schemas.carousel_conflict import (
    CarouselConflictDetail,
    CarouselConflictResponse,
)
from rag_backend.domain.models.carousel_conflict import CarouselConflictError


def carousel_conflict_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    """Serialize a CarouselConflictError additively (legacy + structured)."""
    if not isinstance(exc, CarouselConflictError):
        raise exc
    body = CarouselConflictResponse(
        detail=exc.conflict.code,
        conflict=CarouselConflictDetail.from_domain(exc.conflict),
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=body.model_dump(mode="json"),
    )


def add_carousel_conflict_handler(app: FastAPI) -> None:
    """Register the typed carousel conflict handler."""
    app.add_exception_handler(CarouselConflictError, carousel_conflict_handler)


__all__ = [
    "add_carousel_conflict_handler",
    "carousel_conflict_handler",
]
