"""Domain models for user management."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class User:
    """Represents a system user."""

    id: UUID = field(default_factory=uuid4)
    email: str
    full_name: str
    role: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_editor(self) -> bool:
        return self.role == "editor"

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def set_role(self, role: str) -> None:
        self.role = role
        self.updated_at = datetime.utcnow()
