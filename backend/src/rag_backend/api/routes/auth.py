"""Authentication API routes — thin HTTP adapters over the identity facade.

Each endpoint parses the HTTP request into an identity command, delegates to the
request-scoped :class:`IdentityServices` facade (resolved via the
``get_identity_service`` DI provider at the edge — never the global DI container
or a concrete user repository here), and maps the result back onto the HTTP
response/status. User writes commit through the facade's Unit of Work (the
single commit owner, ADR-0009 §9); these routes never call ``db.commit()``.

Cookies (``access_token`` attributes), the HS256 JWT payload, bcrypt, and status
codes are byte-identical to the pre-refactor routes: the JWT/bcrypt still come
from the UNCHANGED ``infrastructure.auth`` via the identity adapters (AE-0099).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from rag_backend.api.constants import ERR_NOT_AUTHENTICATED
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.dependencies.identity import get_identity_service
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN, MIN_PASSWORD_LENGTH
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.modules.identity import (
    ChangePasswordCommand,
    CurrentPasswordIncorrectError,
    IdentityServices,
    InactiveUserError,
    InvalidCredentialsError,
    LoginCommand,
    User,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_cookie_secure(request: Request, settings: Settings) -> bool:
    """Use Secure cookies only on HTTPS; honor reverse-proxy proto in production."""
    if settings.debug:
        return False
    forwarded = request.headers.get("x-forwarded-proto", "")
    if forwarded:
        return forwarded.split(",")[0].strip().lower() == "https"
    return request.url.scheme == "https"


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Response body containing JWT token."""

    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    """Response body for current user."""

    id: str
    email: str
    full_name: str
    role: str


class ChangePasswordRequest(BaseModel):
    """Request body for changing password."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH)


@router.post(
    "/token",
    response_model=TokenResponse,
    responses={
        401: {"description": "Invalid credentials"},
    },
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[IdentityServices, Depends(get_identity_service)],
) -> TokenResponse:
    """Authenticate user and return JWT access token.

    Sets the token as an HttpOnly cookie for browser clients.
    """
    try:
        token_view = await service.auth.login(
            LoginCommand(email=body.email, password=body.password)
        )
    except (InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    response.set_cookie(
        key=COOKIE_ACCESS_TOKEN,
        value=token_view.access_token,
        httponly=True,
        secure=_auth_cookie_secure(request, settings),
        samesite="strict",
        max_age=settings.access_token_expire_minutes * 60,
    )

    return TokenResponse(access_token=token_view.access_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Log out the current user by clearing the access_token cookie."""
    response.delete_cookie(
        key=COOKIE_ACCESS_TOKEN,
        path="/",
        httponly=True,
        secure=_auth_cookie_secure(request, settings),
        samesite="strict",
    )


@router.get(
    "/me",
    response_model=MeResponse,
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
    },
)
async def get_me(
    user: Annotated[User, Depends(require_authenticated_user)],
) -> MeResponse:
    """Get current authenticated user information."""
    return MeResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
    )


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Invalid current password or not authenticated"},
        400: {"description": "Invalid new password"},
    },
)
async def change_password(
    request: ChangePasswordRequest,
    user: Annotated[User, Depends(require_authenticated_user)],
    service: Annotated[IdentityServices, Depends(get_identity_service)],
) -> None:
    """Change the authenticated user's password."""
    try:
        await service.auth.change_password(
            ChangePasswordCommand(
                user_id=user.id,
                current_password=request.current_password,
                new_password=request.new_password,
            )
        )
    except CurrentPasswordIncorrectError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        ) from exc
