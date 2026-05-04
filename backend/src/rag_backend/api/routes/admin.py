"""Admin API routes for user management."""

import secrets
import string
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from rag_backend.api.dependencies import require_admin
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants import MIN_PASSWORD_LENGTH, ROLE_ADMIN, VALID_ROLES
from rag_backend.domain.models import User, UserRole
from rag_backend.infrastructure.auth import hash_password
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.database.user_repository import PostgresUserRepository

router = APIRouter(prefix="/admin/users", tags=["admin"])


class CreateUserRequest(BaseModel):
    """Request body for creating a user."""

    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(default="editor")
    password: str | None = Field(None, min_length=MIN_PASSWORD_LENGTH)


class UpdateUserRequest(BaseModel):
    """Request body for updating a user."""

    role: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Response body for user."""

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str


class UserListResponse(BaseModel):
    """Response body for list of users."""

    items: list[UserResponse]
    total: int


class CreateUserResponse(BaseModel):
    """Response body for created user with temporary password."""

    id: str
    email: str
    temp_password: str | None = None


class ResetPasswordResponse(BaseModel):
    """Response body for password reset."""

    temp_password: str


def _generate_secure_password(length: int = 16) -> str:
    """Generate a cryptographically secure random password.

    Ensures at least one uppercase, one lowercase, one digit, and one special character.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%^&*" for c in password)
        ):
            return password


def _validate_role(role: str) -> UserRole:
    """Validate role string and return UserRole enum.

    Args:
        role: Role string to validate.

    Returns:
        UserRole enum value.

    Raises:
        HTTPException: If role is invalid.
    """
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role: {role}. Must be one of {sorted(VALID_ROLES)}",
        )
    return UserRole(role)


@router.get(
    "",
    response_model=UserListResponse,
    responses={
        403: {"description": "Admin access required"},
    },
)
@limiter.limit("30/minute")
async def list_users(
    request: Request,
    admin: Annotated[User, Depends(require_admin)],
) -> UserListResponse:
    """List all users. Admin only."""
    from sqlalchemy.ext.asyncio import AsyncSession

    session: AsyncSession
    async for session in get_session():
        repo = PostgresUserRepository(session)
        users = await repo.get_all(limit=1000)
        total = await repo.count()

        return UserListResponse(
            items=[
                UserResponse(
                    id=str(u.id),
                    email=u.email,
                    full_name=u.full_name,
                    role=u.role.value,
                    is_active=u.is_active,
                    created_at=u.created_at.isoformat(),
                )
                for u in users
            ],
            total=total,
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to list users",
    )


@router.post(
    "",
    response_model=CreateUserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"description": "Admin access required"},
        409: {"description": "User already exists"},
    },
)
@limiter.limit("10/minute")
async def create_user(
    request: Request,
    body: CreateUserRequest,
    admin: Annotated[User, Depends(require_admin)],
) -> CreateUserResponse:
    """Create a new user. Admin only.

    If password is not provided, a secure temporary password is generated.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    role = _validate_role(body.role)
    temp_password: str | None = None

    if body.password:
        password = body.password
    else:
        temp_password = _generate_secure_password()
        password = temp_password

    session: AsyncSession
    async for session in get_session():
        repo = PostgresUserRepository(session)

        existing = await repo.get_by_email(body.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {body.email} already exists",
            )

        user = User(
            email=body.email,
            full_name=body.full_name,
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
        )

        created = await repo.create(user)
        await session.commit()

        return CreateUserResponse(
            id=str(created.id),
            email=created.email,
            temp_password=temp_password,
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to create user",
    )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
        409: {"description": "Cannot demote last admin"},
    },
)
@limiter.limit("20/minute")
async def update_user(
    request: Request,
    user_id: UUID,
    body: UpdateUserRequest,
    admin: Annotated[User, Depends(require_admin)],
) -> UserResponse:
    """Update a user. Admin only."""
    from sqlalchemy.ext.asyncio import AsyncSession

    session: AsyncSession
    async for session in get_session():
        repo = PostgresUserRepository(session)

        user = await repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )

        if body.role is not None:
            new_role = _validate_role(body.role)

            # Prevent demoting the last admin
            if user.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
                admin_count = await repo.count_by_role(UserRole.ADMIN)
                if admin_count <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Cannot demote the last admin",
                    )

            user.set_role(new_role)

        if body.is_active is not None:
            if body.is_active:
                user.activate()
            else:
                user.deactivate()

        updated = await repo.update(user)
        await session.commit()

        return UserResponse(
            id=str(updated.id),
            email=updated.email,
            full_name=updated.full_name,
            role=updated.role.value,
            is_active=updated.is_active,
            created_at=updated.created_at.isoformat(),
        )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to update user",
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
        409: {"description": "Cannot delete last admin or self"},
    },
)
@limiter.limit("20/minute")
async def delete_user(
    request: Request,
    user_id: UUID,
    admin: Annotated[User, Depends(require_admin)],
) -> None:
    """Delete a user. Admin only."""
    from sqlalchemy.ext.asyncio import AsyncSession

    # Prevent self-deletion
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete your own account",
        )

    session: AsyncSession
    async for session in get_session():
        repo = PostgresUserRepository(session)

        user = await repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )

        # Prevent deleting the last admin
        if user.role == UserRole.ADMIN:
            admin_count = await repo.count_by_role(UserRole.ADMIN)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot delete the last admin",
                )

        await repo.delete(user_id)
        await session.commit()
        return

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to delete user",
    )


@router.post(
    "/{user_id}/reset-password",
    response_model=ResetPasswordResponse,
    responses={
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
    },
)
@limiter.limit("10/minute")
async def reset_password(
    request: Request,
    user_id: UUID,
    admin: Annotated[User, Depends(require_admin)],
) -> ResetPasswordResponse:
    """Reset a user's password. Admin only.

    Generates a new temporary password for the user.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    session: AsyncSession
    async for session in get_session():
        repo = PostgresUserRepository(session)

        user = await repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )

        temp_password = _generate_secure_password()
        user.hashed_password = hash_password(temp_password)
        await repo.update(user)
        await session.commit()

        return ResetPasswordResponse(temp_password=temp_password)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to reset password",
    )
