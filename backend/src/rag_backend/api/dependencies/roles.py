"""Role-based access control dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.models import UserModel

security = HTTPBearer()


async def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    """Verify JWT token and return user info.
    
    In production, this would validate the JWT signature and expiration.
    For now, we assume the token is valid and return mock user data.
    """
    # In production, decode and validate JWT here
    # For now, return mock user
    return {
        "user_id": "test-user-id",
        "email": "test@example.com",
        "role": UserRole.ADMIN.value,
    }


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserModel:
    """Get current user from token."""
    user_info = await verify_token(credentials)
    
    user = await db.get(UserModel, user_info["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    return user


async def require_role(
    current_user: UserModel = Depends(get_current_user),
    allowed_roles: list[UserRole] = [UserRole.ADMIN, UserRole.EDITOR],
) -> UserModel:
    """Require user to have one of the specified roles."""
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


async def require_admin(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Require user to be an admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_editor(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Require user to be an editor or admin."""
    if current_user.role not in [UserRole.ADMIN, UserRole.EDITOR]:
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
    "CurrentUser",
    "AdminUser",
    "EditorUser",
    "RoleUser",
    "get_current_user",
    "require_admin",
    "require_editor",
    "require_role",
    "verify_token",
]
