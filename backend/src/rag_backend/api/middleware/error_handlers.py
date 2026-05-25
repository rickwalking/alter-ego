"""Error handling middleware for FastAPI."""

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from rag_backend.api.schemas import ErrorResponse
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


async def validation_error_handler(
    _request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = [
        {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="Validation Error",
            message="Invalid input data",
            details={"errors": errors},
        ).model_dump(),
    )


async def sqlalchemy_error_handler(
    _request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    logger.error("database_error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Database Error",
            message="An error occurred while accessing the database",
            details=None,
        ).model_dump(),
    )


async def integrity_error_handler(
    _request: Request, exc: IntegrityError
) -> JSONResponse:
    """Handle database integrity errors."""
    logger.error("integrity_error", error=str(exc))
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            error="Conflict",
            message="A conflict occurred with the current state of the resource",
            details=None,
        ).model_dump(),
    )


async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handle generic exceptions."""
    logger.error("unexpected_error", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            message="An unexpected error occurred",
            details=None,
        ).model_dump(),
    )


def add_error_handlers(app) -> None:
    """Add error handlers to the FastAPI app."""
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
