from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from rag_backend.domain.clock import utc_now
from rag_backend.domain.constants import ROLE_ADMIN, ROLE_EDITOR


class UserField(StrEnum):
    """The persisted user fields a save writes when they change.

    Each value is the attribute name on both the entity and the table model
    (``CREDENTIAL_HASH`` is the password hash, ``SESSION_VERSION`` the token
    version that logs sessions out).
    """

    EMAIL = "email"
    FULL_NAME = "full_name"
    CREDENTIAL_HASH = "hashed_password"
    ROLE = "role"
    IS_ACTIVE = "is_active"
    CREDENTIAL_CHANGE_REQUIRED = "must_change_password"
    SESSION_VERSION = "token_version"
    UPDATED_AT = "updated_at"


_TRACKED_FIELDS = frozenset(UserField)


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
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    must_change_password: bool = False
    token_version: int = 0
    _changed: set[UserField] = field(
        default_factory=set, init=False, repr=False, compare=False
    )
    _tracking: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Start recording assignments once every field holds its initial value."""
        self._tracking = True

    def __setattr__(self, name: str, value: object) -> None:
        """Assign the attribute and, after construction, record a persisted field.

        Recording every assignment (mutator or direct) is what lets a save write
        only the changed columns, so a save never puts back a value it did not
        change, such as a password hash or token version committed meanwhile.
        """
        object.__setattr__(self, name, value)
        if name in _TRACKED_FIELDS and self.__dict__.get("_tracking", False):
            self._changed.add(UserField(name))

    def changed_fields(self) -> frozenset[UserField]:
        """The persisted fields assigned since this entity was built."""
        return frozenset(self._changed)

    def is_admin(self) -> bool:
        """Return True when the user has the admin role."""
        return self.role == UserRole.ADMIN

    def is_editor(self) -> bool:
        """Return True when the user has the editor role."""
        return self.role == UserRole.EDITOR

    def deactivate(self) -> None:
        """Mark the user inactive and refresh the updated timestamp."""
        self.is_active = False
        self.updated_at = utc_now()

    def activate(self) -> None:
        """Mark the user active and refresh the updated timestamp."""
        self.is_active = True
        self.updated_at = utc_now()

    def set_role(self, role: UserRole) -> None:
        """Assign a new role and refresh the updated timestamp."""
        self.role = role
        self.updated_at = utc_now()

    def reset_password(self, hashed_password: str) -> None:
        """Store an admin-issued temporary hash; the user must change it next.

        Also bumps the token version, so every access token issued to the user
        before the reset is refused from now on.
        """
        self.hashed_password = hashed_password
        self.must_change_password = True
        self.token_version += 1

    def change_password(self, hashed_password: str) -> None:
        """Store the user's own new hash and clear the forced-change flag.

        Also bumps the token version, so every access token issued before the
        change is refused from now on.
        """
        self.hashed_password = hashed_password
        self.must_change_password = False
        self.token_version += 1

    def change_email(self, email: str) -> None:
        """Change the email address and refresh the updated timestamp."""
        self.email = email
        self.updated_at = utc_now()

    def rename(self, full_name: str) -> None:
        """Change the display name and refresh the updated timestamp."""
        self.full_name = full_name
        self.updated_at = utc_now()
