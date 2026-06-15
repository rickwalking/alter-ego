"""Public view DTOs exposed across the identity module boundary.

These boundary-safe shapes are what other modules and inbound adapters consume
via the facade. They decouple consumers from the module's internal aggregate
(``User``).

During the behavior-preserving phase (AE-0098) the HTTP routes still return the
legacy response models directly; these views are the boundary contract the
routes adopt when they move behind the facade (AE-0099). This phase introduces
no response change.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# OAuth2 bearer scheme label for issued access tokens (mirrors the legacy
# ``TokenResponse.token_type`` default so the wire shape is unchanged).
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
