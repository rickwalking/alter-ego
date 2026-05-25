"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from rag_backend.api.constants import ERR_NOT_AUTHENTICATED
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN, MIN_PASSWORD_LENGTH
from rag_backend.domain.models import User
from rag_backend.infrastructure.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.database.user_repository import PostgresUserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


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
) -> TokenResponse:
    """Authenticate user and return JWT access token.

    Sets the token as an HttpOnly cookie for browser clients.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    session: AsyncSession
    async for session in get_session():
        repo = PostgresUserRepository(session)
        user = await repo.get_by_email(body.email)

        if user is None or not verify_password(body.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is deactivated",
            )

        token = create_access_token(settings, user)

        response.set_cookie(
            key=COOKIE_ACCESS_TOKEN,
            value=token,
            httponly=True,
            secure=not settings.debug,
            samesite="strict",
            max_age=settings.access_token_expire_minutes * 60,
        )

        return TokenResponse(access_token=token)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to create session",
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Log out the current user by clearing the access_token cookie."""
    response.delete_cookie(
        key=COOKIE_ACCESS_TOKEN,
        path="/",
        httponly=True,
        secure=not settings.debug,
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
) -> None:
    """Change the authenticated user's password."""
    if not verify_password(request.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    from sqlalchemy.ext.asyncio import AsyncSession

    session: AsyncSession
    async for session in get_session():
        repo = PostgresUserRepository(session)
        user.hashed_password = hash_password(request.new_password)
        await repo.update(user)
        await session.commit()
        return

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to update password",
    )
