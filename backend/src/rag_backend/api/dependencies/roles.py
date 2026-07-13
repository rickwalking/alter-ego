"""Role-based access control dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import ERR_NOT_AUTHENTICATED
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.middleware.auth import get_current_user as get_jwt_payload
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.models import UserModel


async def get_current_user(
    payload: Annotated[dict[str, str], Depends(get_jwt_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserModel:
    """Resolve the authenticated user from a validated JWT payload."""
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERR_NOT_AUTHENTICATED,
        )

    user = await db.get(UserModel, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERR_NOT_AUTHENTICATED,
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
        )
    return user


async def require_role(
    current_user: UserModel = Depends(get_current_user),
    allowed_roles: list[UserRole] | None = None,
) -> UserModel:
    """Require user to have one of the specified roles."""
    roles = allowed_roles or [UserRole.ADMIN, UserRole.EDITOR]
    allowed_values = {role.value for role in roles}
    if current_user.role not in allowed_values:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


async def require_admin(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Require user to be an admin."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_editor(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Require user to be an editor or admin."""
    if current_user.role not in {UserRole.ADMIN.value, UserRole.EDITOR.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor access required",
        )
    return current_user


# Type aliases for use in route dependencies
CurrentUser = Annotated[UserModel, Depends(get_current_user)]
AdminUser = Annotated[UserModel, Depends(require_admin)]
EditorUser = Annotated[UserModel, Depends(require_editor)]
RoleUser = Annotated[UserModel, Depends(require_role)]


__all__ = [
    "AdminUser",
    "CurrentUser",
    "EditorUser",
    "RoleUser",
    "UserModel",
    "get_current_user",
    "require_admin",
    "require_editor",
    "require_role",
]
