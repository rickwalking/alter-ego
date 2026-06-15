"""Admin API routes for user management — thin adapters over the identity facade.

Each endpoint parses the HTTP request into an identity admin command, delegates
to the request-scoped :class:`IdentityServices` facade (resolved via the
``get_identity_service`` DI provider at the edge — never the global DI container
or a concrete user repository here), and maps the handler's view/typed errors
back onto the HTTP response/status. User writes commit through the facade's Unit
of Work (the single commit owner, ADR-0009 §9); these routes never call
``db.commit()``.

Status codes, response shapes, bcrypt, and the last-admin / self-delete guards
are byte-identical to the pre-refactor routes (AE-0099): bcrypt still comes from
the UNCHANGED ``infrastructure.auth`` via the identity adapters, and the legacy
HTTP messages are formatted here from the handler's typed domain errors.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from rag_backend.api.dependencies import require_admin
from rag_backend.api.dependencies.identity import get_identity_service
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.domain.constants import MIN_PASSWORD_LENGTH
from rag_backend.domain.constants.auth import VALID_ROLES
from rag_backend.modules.identity import (
    CreateUserInput,
    DeleteUserInput,
    IdentityServices,
    InvalidRoleError,
    LastAdminError,
    SelfDeleteError,
    UpdateUserInput,
    User,
    UserAlreadyExistsError,
    UserListView,
    UserNotFoundError,
    UserView,
)

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


def _invalid_role(exc: InvalidRoleError) -> HTTPException:
    """Map an invalid-role domain error to the legacy 422 response."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Invalid role: {exc.role}. Must be one of {sorted(VALID_ROLES)}",
    )


def _not_found(user_id: UUID) -> HTTPException:
    """Map a missing-user domain error to the legacy 404 response."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"User with id {user_id} not found",
    )


def _to_response(view: UserView) -> UserResponse:
    """Map an identity user view onto the legacy user response shape."""
    return UserResponse(
        id=str(view.id),
        email=view.email,
        full_name=view.full_name,
        role=view.role,
        is_active=view.is_active,
        created_at=view.created_at.isoformat(),
    )


def _to_list_response(listing: UserListView) -> UserListResponse:
    """Map an identity user-list view onto the legacy list response shape."""
    return UserListResponse(
        items=[_to_response(item) for item in listing.items],
        total=listing.total,
    )


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
    service: Annotated[IdentityServices, Depends(get_identity_service)],
) -> UserListResponse:
    """List all users. Admin only."""
    return _to_list_response(await service.admin.list_users())


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
    service: Annotated[IdentityServices, Depends(get_identity_service)],
) -> CreateUserResponse:
    """Create a new user. Admin only.

    If password is not provided, a secure temporary password is generated.
    """
    try:
        created = await service.admin.create(
            CreateUserInput(
                email=body.email,
                full_name=body.full_name,
                role=body.role,
                password=body.password,
            )
        )
    except InvalidRoleError as exc:
        raise _invalid_role(exc) from exc
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {body.email} already exists",
        ) from exc

    return CreateUserResponse(
        id=str(created.id),
        email=created.email,
        temp_password=created.temp_password,
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
    service: Annotated[IdentityServices, Depends(get_identity_service)],
) -> UserResponse:
    """Update a user. Admin only."""
    try:
        updated = await service.admin.update(
            UpdateUserInput(
                user_id=user_id,
                role=body.role,
                is_active=body.is_active,
            )
        )
    except InvalidRoleError as exc:
        raise _invalid_role(exc) from exc
    except UserNotFoundError as exc:
        raise _not_found(user_id) from exc
    except LastAdminError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot demote the last admin",
        ) from exc

    return _to_response(updated)


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
    service: Annotated[IdentityServices, Depends(get_identity_service)],
) -> None:
    """Delete a user. Admin only."""
    try:
        await service.admin.delete(
            DeleteUserInput(user_id=user_id, requested_by=admin.id)
        )
    except SelfDeleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete your own account",
        ) from exc
    except UserNotFoundError as exc:
        raise _not_found(user_id) from exc
    except LastAdminError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete the last admin",
        ) from exc


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
    service: Annotated[IdentityServices, Depends(get_identity_service)],
) -> ResetPasswordResponse:
    """Reset a user's password. Admin only.

    Generates a new temporary password for the user.
    """
    try:
        temp_password = await service.admin.reset_password(user_id)
    except UserNotFoundError as exc:
        raise _not_found(user_id) from exc

    return ResetPasswordResponse(temp_password=temp_password)
