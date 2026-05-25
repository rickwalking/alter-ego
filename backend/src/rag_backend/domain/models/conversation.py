"""Domain models for chat conversation management."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Conversation:
    """Represents a user conversation session."""

    id: UUID = field(default_factory=uuid4)
    user_id: str
    title: str
    messages: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Message:
    """Represents a message within a conversation."""

    id: UUID = field(default_factory=uuid4)
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Message:
    """Represents a message within a conversation."""

    id: UUID = field(default_factory=uuid4)
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    sources: list[dict[str, str | int | float | bool]] = field(default_factory=list)


@dataclass
class Conversation:
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    user_id: UUID | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

    def update_title(self, title: str) -> None:
        self.title = title
        self.updated_at = datetime.utcnow()

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
