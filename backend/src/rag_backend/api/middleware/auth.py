"""Authentication middleware and dependencies."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from rag_backend.infrastructure.auth import (
    decode_access_token,
    decode_anonymous_token,
)
from rag_backend.infrastructure.config.settings import Settings, get_settings

security = HTTPBearer(auto_error=False)


def _extract_token_from_request(request: Request) -> str | None:
    """Extract JWT token from Authorization header or cookie."""
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:]

    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    return None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Validate JWT token and return current user payload.

    Checks Bearer header first, then falls back to access_token cookie.

    Args:
        request: FastAPI request object.
        credentials: HTTP Bearer token credentials.
        settings: Application settings.

    Returns:
        Token payload dict with user information.

    Raises:
        HTTPException: If token is missing or invalid.
    """
    token = credentials.credentials if credentials else _extract_token_from_request(request)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(settings, token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> dict[str, str] | None:
    """Validate JWT token if present, otherwise return None.

    Args:
        request: FastAPI request object.
        credentials: HTTP Bearer token credentials.
        settings: Application settings.

    Returns:
        Token payload dict if valid, None otherwise.
    """
    token = credentials.credentials if credentials else _extract_token_from_request(request)

    if not token:
        return None

    return decode_access_token(settings, token)


async def get_anonymous_payload(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, object] | None:
    """Validate anonymous JWT token from query param or cookie.

    Args:
        request: FastAPI request object.
        settings: Application settings.

    Returns:
        Anonymous token payload dict if valid, None otherwise.
    """
    token = request.query_params.get("token")
    if not token:
        token = request.cookies.get("anon_token")

    if not token:
        return None

    return decode_anonymous_token(settings, token)
