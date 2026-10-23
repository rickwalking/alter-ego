from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from rag_backend.domain.clock import utc_now
from rag_backend.domain.constants.conversation import (
    CONVERSATION_TITLE_ELLIPSIS,
    CONVERSATION_TITLE_MAX_LENGTH,
)


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
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)
    sources: list[dict[str, str | int | float | bool]] = field(default_factory=list)


@dataclass
class Conversation:
    id: UUID = field(default_factory=uuid4)
    title: str | None = None
    user_id: UUID | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

    def update_title(self, title: str) -> None:
        self.title = title
        self.updated_at = utc_now()

    def ensure_title_from(self, first_message: str) -> bool:
        """Title an untitled conversation from its first message.

        The first line, whitespace collapsed, cut at
        ``CONVERSATION_TITLE_MAX_LENGTH`` with an ellipsis. Returns whether the
        title changed (an existing title is never replaced).
        """
        if self.title and self.title.strip():
            return False
        first_line = " ".join(first_message.strip().splitlines()[:1]).split()
        title = " ".join(first_line)
        if not title:
            return False
        if len(title) > CONVERSATION_TITLE_MAX_LENGTH:
            cut = title[: CONVERSATION_TITLE_MAX_LENGTH - 1].rstrip()
            title = f"{cut}{CONVERSATION_TITLE_ELLIPSIS}"
        self.update_title(title)
        return True

    def touch(self) -> None:
        self.updated_at = utc_now()
