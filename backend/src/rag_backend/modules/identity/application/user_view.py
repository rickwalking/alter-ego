"""Project the identity ``User`` aggregate to its boundary-safe ``UserView``."""

from __future__ import annotations

from rag_backend.modules.identity.api.views import UserView
from rag_backend.modules.identity.domain.models import User


def to_user_view(user: User) -> UserView:
    """The boundary-safe projection of ``user`` (never exposes the hash)."""
    return UserView(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
