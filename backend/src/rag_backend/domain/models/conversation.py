from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    role: MessageRole
    content: str
    conversation_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    sources: list[dict[str, str | int | float | bool]] = field(default_factory=list)


@dataclass
class Conversation:
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

    def update_title(self, title: str) -> None:
        self.title = title
        self.updated_at = datetime.utcnow()

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
