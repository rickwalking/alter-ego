"""Authentication and authorization FastAPI dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    ERR_ADMIN_REQUIRED,
    ERR_CODE_PASSWORD_CHANGE_REQUIRED,
    ERR_PASSWORD_CHANGE_REQUIRED,
    ERR_USER_NOT_FOUND,
)
from rag_backend.api.middleware.auth import get_current_user, get_current_user_optional
from rag_backend.api.middleware.coded_error_handler import CodedHTTPException
from rag_backend.domain.models import User
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.database.user_repository import PostgresUserRepository


async def get_request_session(
    db: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncSession:
    """Expose the per-request session to edge providers (e.g. the identity facade).

    ``Depends(get_session)`` is cached per request by FastAPI, so the session
    returned here is the SAME object :func:`get_user_repo` binds its repository
    to. The identity DI provider uses this to enlist that one session in the
    platform Unit of Work, keeping repository flushes and the UoW commit in a
    single transaction without importing ``infrastructure.database.config``.
    """
    return db


async def get_user_repo(
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PostgresUserRepository:
    """Get user repository bound to the per-request session."""
    return PostgresUserRepository(db)


async def require_signed_in_user(
    payload: Annotated[dict[str, str], Depends(get_current_user)],
    repo: Annotated[PostgresUserRepository, Depends(get_user_repo)],
) -> User:
    """Require a signed-in, active user, even one who must change the password.

    Only ``/api/auth/me`` and ``/api/auth/change-password`` use this directly;
    every other protected endpoint goes through
    :func:`require_authenticated_user`, which also refuses a user who must
    change the password first.

    Args:
        payload: JWT payload from get_current_user.
        repo: User repository.

    Returns:
        Authenticated User entity.

    Raises:
        HTTPException: If user not found or inactive.
    """
    user_id = UUID(payload["sub"])
    user = await repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERR_USER_NOT_FOUND,
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
        )

    return user


def reject_pending_password_change(*, must_change_password: bool) -> None:
    """Refuse a user who must change an admin-issued password first (403)."""
    if must_change_password:
        raise CodedHTTPException(
            status.HTTP_403_FORBIDDEN,
            ERR_PASSWORD_CHANGE_REQUIRED,
            ERR_CODE_PASSWORD_CHANGE_REQUIRED,
        )


async def require_authenticated_user(
    user: Annotated[User, Depends(require_signed_in_user)],
) -> User:
    """Require an authenticated user who may use the app.

    A user whose password an admin reset is refused with 403
    ``password_change_required`` until they change it.

    Raises:
        HTTPException: 401 if not signed in, 403 if the password must change.
    """
    reject_pending_password_change(must_change_password=user.must_change_password)
    return user


async def require_admin(
    user: Annotated[User, Depends(require_authenticated_user)],
) -> User:
    """Require admin role.

    Args:
        user: Authenticated user.

    Returns:
        Admin user.

    Raises:
        HTTPException: 403 if user is not admin.
    """
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_ADMIN_REQUIRED,
        )
    return user


async def require_editor_or_admin(
    user: Annotated[User, Depends(require_authenticated_user)],
) -> User:
    """Require editor or admin role.

    Args:
        user: Authenticated user.

    Returns:
        User if role is editor or admin.

    Raises:
        HTTPException: 403 if user is not editor or admin.
    """
    if not (user.is_editor() or user.is_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor or admin access required",
        )
    return user


def require_owner_or_admin(
    resource_owner_id: UUID | None,
    user: User,
) -> None:
    """Check if user is owner of resource or admin.

    Args:
        resource_owner_id: Owner ID of the resource.
        user: Current authenticated user.

    Raises:
        HTTPException: 403 if user is not owner and not admin.
    """
    if user.is_admin():
        return

    if resource_owner_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if resource_owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: not the resource owner",
        )


async def get_optional_user(
    payload: Annotated[dict[str, str] | None, Depends(get_current_user_optional)],
    repo: Annotated[PostgresUserRepository, Depends(get_user_repo)],
) -> User | None:
    """Get authenticated user if present, otherwise None.

    Args:
        payload: Optional JWT payload.
        repo: User repository.

    Returns:
        User entity if authenticated, None otherwise. A user who must change
        the password is treated as an anonymous visitor.
    """
    if payload is None:
        return None

    user_id = UUID(payload["sub"])
    user = await repo.get_by_id(user_id)

    if user is None or not user.is_active or user.must_change_password:
        return None

    return user


__all__ = [
    "get_optional_user",
    "get_request_session",
    "get_user_repo",
    "reject_pending_password_change",
    "require_admin",
    "require_authenticated_user",
    "require_editor_or_admin",
    "require_owner_or_admin",
    "require_signed_in_user",
]
