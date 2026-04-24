"""Authentication middleware and dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from rag_backend.infrastructure.auth import decode_access_token
from rag_backend.infrastructure.config.settings import Settings, get_settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Validate JWT token and return current user payload.

    Use this as a dependency in protected routes.

    Args:
        credentials: HTTP Bearer token credentials.
        settings: Application settings.

    Returns:
        Token payload dict with user information.

    Raises:
        HTTPException: If token is missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(settings, credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> dict[str, str] | None:
    """Validate JWT token if present, otherwise return None.

    Use this for routes that work with or without authentication.

    Args:
        credentials: HTTP Bearer token credentials.
        settings: Application settings.

    Returns:
        Token payload dict if valid, None otherwise.
    """
    if credentials is None:
        return None

    return decode_access_token(settings, credentials.credentials)
