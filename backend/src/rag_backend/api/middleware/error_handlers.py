"""Error handling middleware for FastAPI."""

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from rag_backend.api.schemas import ErrorResponse


async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="Validation Error",
            message="Invalid input data",
            details={"errors": errors},
        ).model_dump(),
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Handle SQLAlchemy database errors."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Database Error",
            message="An error occurred while accessing the database",
            details={"detail": str(exc)} if isinstance(exc, SQLAlchemyError) else None,
        ).model_dump(),
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors."""
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            error="Conflict",
            message="A conflict occurred with the current state of the resource",
            details={"detail": str(exc.orig) if hasattr(exc, "orig") else str(exc)},
        ).model_dump(),
    )


async def generic_error_handler(request: Request, exc: Exception):
    """Handle generic exceptions."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            message="An unexpected error occurred",
            details={"detail": str(exc)} if isinstance(exc, Exception) else None,
        ).model_dump(),
    )


def add_error_handlers(app):
    """Add error handlers to the FastAPI app."""
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
