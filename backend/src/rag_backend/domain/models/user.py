from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from rag_backend.domain.constants import ROLE_ADMIN, ROLE_EDITOR


class UserRole(StrEnum):
    """Application roles used for authorization checks."""

    ADMIN = ROLE_ADMIN
    EDITOR = ROLE_EDITOR


@dataclass
class User:
    """Authenticated account with role-based access control."""

    email: str
    full_name: str
    hashed_password: str
    role: UserRole = UserRole.EDITOR
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def is_admin(self) -> bool:
        """Return True when the user has the admin role."""
        return self.role == UserRole.ADMIN

    def is_editor(self) -> bool:
        """Return True when the user has the editor role."""
        return self.role == UserRole.EDITOR

    def deactivate(self) -> None:
        """Mark the user inactive and refresh the updated timestamp."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Mark the user active and refresh the updated timestamp."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def set_role(self, role: UserRole) -> None:
        """Assign a new role and refresh the updated timestamp."""
        self.role = role
        self.updated_at = datetime.utcnow()
