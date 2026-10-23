"""Rate limiting middleware using slowapi."""

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from rag_backend.domain.constants.rate_limits import (
    RATE_LIMIT_USER_KEY_PREFIX,
    RATE_LIMIT_USER_STATE,
)
from rag_backend.infrastructure.config.settings import Settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
)


def user_or_address_key(request: Request) -> str:
    """The user id a route dependency recorded on the request, else the address."""
    user_id = getattr(request.state, RATE_LIMIT_USER_STATE, None)
    if not user_id:
        return get_remote_address(request)
    return f"{RATE_LIMIT_USER_KEY_PREFIX}{user_id}"


def setup_rate_limiting(app, _settings: Settings) -> None:
    """Configure rate limiting on the FastAPI app.

    Args:
        app: The FastAPI application instance
        settings: Application settings
    """
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _rate_limit_exceeded_handler(_request, exc):
    """Handle rate limit exceeded errors."""
    from fastapi.responses import JSONResponse

    from rag_backend.api.schemas import ErrorResponse

    return JSONResponse(
        status_code=429,
        content=ErrorResponse(
            error="Rate Limit Exceeded",
            message="Too many requests. Please try again later.",
            details={"retry_after": getattr(exc, "retry_after", None)},
        ).model_dump(),
    )
