"""Authentication middleware and dependencies."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from rag_backend.api.constants import (
    ERR_INVALID_OR_EXPIRED_TOKEN,
    ERR_NOT_AUTHENTICATED,
    WWW_AUTHENTICATE_BEARER,
)
from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN, COOKIE_ANON_TOKEN
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

    cookie_token = request.cookies.get(COOKIE_ACCESS_TOKEN)
    if cookie_token:
        return cookie_token

    return None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """Validate JWT token and return current user payload.

    Checks Bearer header first, then falls back to access_token cookie. Only
    the signature, type and expiry are checked here; the token version is
    checked against the user by the dependencies that load the user
    (``api.dependencies.token_version``).

    Args:
        request: FastAPI request object.
        credentials: HTTP Bearer token credentials.
        settings: Application settings.

    Returns:
        Token payload dict with user information.

    Raises:
        HTTPException: If token is missing or invalid.
    """
    token = (
        credentials.credentials if credentials else _extract_token_from_request(request)
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERR_NOT_AUTHENTICATED,
            headers=WWW_AUTHENTICATE_BEARER,
        )

    payload = decode_access_token(settings, token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERR_INVALID_OR_EXPIRED_TOKEN,
            headers=WWW_AUTHENTICATE_BEARER,
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
    token = (
        credentials.credentials if credentials else _extract_token_from_request(request)
    )

    if not token:
        return None

    return decode_access_token(settings, token)


_COOKIE_HEADER = "cookie"


def _anon_cookie_tokens(request: Request) -> list[str]:
    """Every ``anon_token`` value in the Cookie header.

    A browser may send several (a conversation-scoped one and, until it
    expires, an older site-wide one); a plain cookie dict would keep only one.
    """
    tokens: list[str] = []
    for part in request.headers.get(_COOKIE_HEADER, "").split(";"):
        name, _, value = part.strip().partition("=")
        if name == COOKIE_ANON_TOKEN and value:
            tokens.append(value)
    return tokens


async def get_anon_cookie_payloads(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> list[dict[str, object]]:
    """Decoded payloads of the valid ``anon_token`` cookies (never a URL token).

    Only the HttpOnly cookie counts as a write credential: a token in the
    query string would end up in access logs and referrers.
    """
    payloads = (
        decode_anonymous_token(settings, token)
        for token in _anon_cookie_tokens(request)
    )
    return [payload for payload in payloads if payload is not None]
