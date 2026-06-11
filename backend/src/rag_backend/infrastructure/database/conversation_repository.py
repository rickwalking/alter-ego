"""PostgreSQL repository implementations for Conversation and Message."""

from typing import TypedDict, TypeVar
from uuid import UUID

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from rag_backend.domain.constants.conversation import (
    CONVERSATION_METADATA_PROJECT_ID,
    CONVERSATION_ORIGIN_FILTER_ALTER_EGO,
)
from rag_backend.domain.models import Conversation, Message
from rag_backend.infrastructure.database.models import (
    ConversationModel,
    MessageModel,
)

_ERR_CONVERSATION_NOT_FOUND = "Conversation with id {} not found"

_SelectRow = TypeVar("_SelectRow", bound=tuple[object, ...])


class _UserQuery(TypedDict, total=False):
    """Bundled query parameters for user conversation listing."""

    user_id: UUID
    limit: int
    offset: int
    origin: str | None


class PostgresConversationRepository:
    """PostgreSQL implementation of ConversationRepository protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, conversation: Conversation) -> Conversation:
        """Create a new conversation."""
        db_conversation = ConversationModel.from_entity(conversation)
        self._session.add(db_conversation)
        await self._session.flush()
        return db_conversation.to_entity()

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        """Get a conversation by its ID."""
        result = await self._session.execute(
            select(ConversationModel).where(
                ConversationModel.id == str(conversation_id)
            )
        )
        db_conversation = result.scalar_one_or_none()
        return db_conversation.to_entity() if db_conversation else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[Conversation]:
        """Get all conversations ordered by updated_at desc."""
        result = await self._session.execute(
            select(ConversationModel)
            .order_by(desc(ConversationModel.updated_at))
            .offset(offset)
            .limit(limit)
        )
        return [conv.to_entity() for conv in result.scalars().all()]

    def _apply_origin_filter(
        self, stmt: Select[_SelectRow], origin: str | None
    ) -> Select[_SelectRow]:
        if origin != CONVERSATION_ORIGIN_FILTER_ALTER_EGO:
            return stmt
        return stmt.where(
            or_(
                ConversationModel.conv_metadata.is_(None),
                ConversationModel.conv_metadata[CONVERSATION_METADATA_PROJECT_ID].is_(
                    None
                ),
            )
        )

    async def get_by_user_id(
        self,
        query: _UserQuery,
    ) -> list[Conversation]:
        """Get conversations owned by a user."""
        user_id = query["user_id"]
        limit = query.get("limit", 100)
        offset = query.get("offset", 0)
        origin = query.get("origin")
        stmt = (
            select(ConversationModel)
            .where(ConversationModel.owner_id == str(user_id))
            .order_by(desc(ConversationModel.updated_at))
            .offset(offset)
            .limit(limit)
        )
        stmt = self._apply_origin_filter(stmt, origin)
        result = await self._session.execute(stmt)
        return [conv.to_entity() for conv in result.scalars().all()]

    async def count_by_user_id(self, user_id: UUID, origin: str | None = None) -> int:
        """Count conversations owned by a user."""
        stmt = (
            select(func.count())
            .select_from(ConversationModel)
            .where(ConversationModel.owner_id == str(user_id))
        )
        stmt = self._apply_origin_filter(stmt, origin)
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def update(self, conversation: Conversation) -> Conversation:
        """Update an existing conversation."""
        result = await self._session.execute(
            select(ConversationModel).where(
                ConversationModel.id == str(conversation.id)
            )
        )
        db_conversation = result.scalar_one_or_none()
        if not db_conversation:
            raise ValueError(_ERR_CONVERSATION_NOT_FOUND.format(conversation.id))

        db_conversation.update_from_entity(conversation)
        await self._session.flush()
        return db_conversation.to_entity()

    async def delete(self, conversation_id: UUID) -> bool:
        """Delete a conversation and all its messages."""
        result = await self._session.execute(
            select(ConversationModel).where(
                ConversationModel.id == str(conversation_id)
            )
        )
        db_conversation = result.scalar_one_or_none()
        if not db_conversation:
            return False

        await self._session.delete(db_conversation)
        await self._session.flush()
        return True


class PostgresMessageRepository:
    """PostgreSQL implementation of MessageRepository protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, message: Message) -> Message:
        """Create a new message."""
        db_message = MessageModel.from_entity(message)
        self._session.add(db_message)
        await self._session.flush()
        return db_message.to_entity()

    async def get_by_conversation(
        self, conversation_id: UUID, limit: int = 100
    ) -> list[Message]:
        """Get all messages for a conversation."""
        result = await self._session.execute(
            select(MessageModel)
            .where(MessageModel.conversation_id == str(conversation_id))
            .order_by(MessageModel.created_at)
            .limit(limit)
        )
        return [msg.to_entity() for msg in result.scalars().all()]

    async def count_by_conversation(self, conversation_id: UUID) -> int:
        """Count messages in a conversation."""
        result = await self._session.execute(
            select(func.count()).where(
                MessageModel.conversation_id == str(conversation_id)
            )
        )
        return result.scalar() or 0

    async def get_recent_context(
        self, conversation_id: UUID, max_tokens: int = 4000
    ) -> list[Message]:
        """Get recent messages that fit within token limit.

        This is a simplified implementation that returns the most recent messages
        up to a reasonable count. A more sophisticated implementation would
        calculate actual token counts.
        """
        # Estimate ~100 tokens per message on average
        estimated_messages = max_tokens // 100

        result = await self._session.execute(
            select(MessageModel)
            .where(MessageModel.conversation_id == str(conversation_id))
            .order_by(desc(MessageModel.created_at))
            .limit(estimated_messages)
        )
        messages = list(result.scalars().all())
        # Reverse to maintain chronological order
        messages.reverse()
        return [msg.to_entity() for msg in messages]
