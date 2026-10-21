"""Public view DTOs exposed across the identity module boundary.

These boundary-safe shapes are what other modules and inbound adapters consume
via the facade. They decouple consumers from the module's internal aggregate
(``User``).

During the behavior-preserving phase the HTTP routes still return the
legacy response models directly; these views are the boundary contract the
routes adopt when they move behind the facade. This phase introduces
no response change.

The bearer token type label mirrors the legacy ``TokenResponse.token_type`` default so
the wire shape is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

_BEARER_SCHEME = "bearer"


@dataclass(frozen=True)
class UserView:
    """Boundary-safe projection of a user account (never exposes the hash)."""

    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class UserListView:
    """Boundary-safe page of users plus the matching total."""

    items: list[UserView]
    total: int


@dataclass(frozen=True)
class AccessTokenView:
    """Boundary-safe issued access token (mirrors the legacy token response)."""

    access_token: str
    token_type: str = _BEARER_SCHEME


__all__ = [
    "AccessTokenView",
    "UserListView",
    "UserView",
]
