"""Projection of the identity User aggregate to its boundary-safe view.

Scenario: the view mirrors the aggregate and never carries the hash.
"""

from __future__ import annotations

from rag_backend.modules.identity.application.user_view import to_user_view
from rag_backend.modules.identity.domain.models import User, UserRole


# Scenario: the view mirrors the aggregate and never carries the hash.
def test_view_mirrors_the_aggregate_without_the_hash() -> None:
    user = User(
        email="a@example.com",
        full_name="Ada",
        hashed_password="secret-hash",
        role=UserRole.ADMIN,
        is_active=False,
    )

    view = to_user_view(user)

    assert (view.id, view.email, view.full_name) == (user.id, "a@example.com", "Ada")
    assert view.role == UserRole.ADMIN.value
    assert view.is_active is False
    assert (view.created_at, view.updated_at) == (user.created_at, user.updated_at)
    assert "secret-hash" not in repr(view)
