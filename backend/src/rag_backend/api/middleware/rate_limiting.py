"""Rate limiting middleware using slowapi."""

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from rag_backend.infrastructure.config.settings import Settings

# Global rate limiter with default limits
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
)


def setup_rate_limiting(app, settings: Settings) -> None:
    """Configure rate limiting on the FastAPI app.

    Args:
        app: The FastAPI application instance
        settings: Application settings
    """
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    # Add rate limit exceeded handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _rate_limit_exceeded_handler(request, exc):
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
