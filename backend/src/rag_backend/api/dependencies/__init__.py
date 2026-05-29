"""FastAPI dependencies for RBAC and resource authorization."""

from rag_backend.api.dependencies.auth import (
    get_optional_user,
    get_user_repo,
    require_admin,
    require_authenticated_user,
    require_editor_or_admin,
    require_owner_or_admin,
)

__all__ = [
    "get_optional_user",
    "get_user_repo",
    "require_admin",
    "require_authenticated_user",
    "require_editor_or_admin",
    "require_owner_or_admin",
]
