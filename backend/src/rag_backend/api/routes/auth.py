"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from rag_backend.infrastructure.auth import create_access_token
from rag_backend.infrastructure.config.settings import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenRequest(BaseModel):
    """Request body for token generation."""

    api_key: str = Field(..., description="API key for authentication")


class TokenResponse(BaseModel):
    """Response body containing JWT token."""

    access_token: str
    token_type: str = "bearer"  # noqa: S105 — field name, not a password


class SetupRequest(BaseModel):
    """Request body for initial setup."""

    api_key: str = Field(..., min_length=8, description="API key to set")


@router.post(
    "/token",
    response_model=TokenResponse,
    responses={
        401: {"description": "Invalid credentials"},
    },
)
async def get_token(request: TokenRequest, settings: Annotated[Settings, Depends(get_settings)]):
    """Exchange an API key for a JWT access token.

    The API key must match the configured secret_key (for simple deployments)
    or be validated against a user database (for production).
    """
    if request.api_key != settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    token = create_access_token(settings, subject="api_user")
    return TokenResponse(access_token=token)
