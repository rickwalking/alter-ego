"""Conversation service with memory management."""

from uuid import UUID

from rag_backend.domain.models import Conversation, Message, MessageRole
from rag_backend.domain.protocols import ConversationRepository, MessageRepository

MAX_TITLE_TOKENS = 100
MAX_FALLBACK_TITLE_LENGTH = 50


class ConversationService:
    """Service for managing conversations and memory."""

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        max_context_tokens: int = 4000,
    ) -> None:
        self._conversation_repository = conversation_repository
        self._message_repository = message_repository
        self._max_context_tokens = max_context_tokens

    async def create_conversation(
        self,
        title: str | None = None,
        metadata: dict[str, object] | None = None,
        user_id: UUID | None = None,
    ) -> Conversation:
        """Create a new conversation.

        Args:
            title: Optional conversation title
            metadata: Optional metadata dictionary
            user_id: Optional owner user UUID

        Returns:
            The created conversation
        """
        conversation = Conversation(
            title=title,
            user_id=user_id,
            metadata=metadata or {},
        )
        return await self._conversation_repository.create(conversation)

    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        """Get a conversation by ID.

        Args:
            conversation_id: The conversation UUID

        Returns:
            The conversation or None if not found
        """
        return await self._conversation_repository.get_by_id(conversation_id)

    async def get_conversation_history(
        self, conversation_id: UUID, limit: int = 50
    ) -> list[Message]:
        """Get message history for a conversation.

        Args:
            conversation_id: The conversation UUID
            limit: Maximum number of messages to retrieve

        Returns:
            List of messages in chronological order
        """
        return await self._message_repository.get_by_conversation(conversation_id, limit=limit)

    async def get_context_window(self, conversation_id: UUID) -> list[dict[str, str]]:
        """Get the context window for the LLM.

        Retrieves messages that fit within the token limit,
        formatted for LangChain/OpenAI.

        Args:
            conversation_id: The conversation UUID

        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        messages = await self._message_repository.get_recent_context(
            conversation_id, max_tokens=self._max_context_tokens
        )

        return [
            {
                "role": msg.role.value,
                "content": msg.content,
            }
            for msg in messages
        ]

    async def add_message(
        self,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        sources: list[dict[str, object]] | None = None,
    ) -> Message:
        """Add a message to a conversation.

        Args:
            conversation_id: The conversation UUID
            role: Message role (user/assistant/system)
            content: Message content
            sources: Optional source documents

        Returns:
            The created message
        """
        message = Message(
            role=role,
            content=content,
            conversation_id=conversation_id,
            sources=sources or [],
        )

        created_message = await self._message_repository.create(message)

        # Update conversation timestamp
        conversation = await self._conversation_repository.get_by_id(conversation_id)
        if conversation:
            conversation.touch()
            await self._conversation_repository.update(conversation)

        return created_message

    async def delete_conversation(self, conversation_id: UUID) -> bool:
        """Delete a conversation and all its messages.

        Args:
            conversation_id: The conversation UUID

        Returns:
            True if deleted successfully
        """
        return await self._conversation_repository.delete(conversation_id)

    async def list_conversations(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: UUID | None = None,
    ) -> list[Conversation]:
        """List conversations, optionally filtered by owner."""
        if user_id is not None:
            return await self._conversation_repository.get_by_user_id(
                user_id=user_id,
                limit=limit,
                offset=offset,
            )
        return await self._conversation_repository.get_all(limit=limit, offset=offset)

    async def count_conversations_for_user(self, user_id: UUID) -> int:
        """Count conversations owned by a user."""
        return await self._conversation_repository.count_by_user_id(user_id)

    async def generate_title(self, conversation_id: UUID, llm_generate_func) -> str:
        """Generate a title for a conversation based on first message.

        Args:
            conversation_id: The conversation UUID
            llm_generate_func: Async function to generate text from LLM

        Returns:
            Generated title
        """
        messages = await self._message_repository.get_by_conversation(conversation_id, limit=1)

        if not messages:
            return "New Conversation"

        first_message = messages[0].content

        # Generate title using LLM
        prompt = (
            "Generate a concise, descriptive title (max 5 words) "
            f"for a conversation that starts with this message:\n\n"
            f"Message: {first_message[:200]}\n\n"
            "Title:"
        )

        try:
            title = await llm_generate_func([{"role": "user", "content": prompt}])
            title = title.strip().strip('"').strip("'")

            if len(title) > MAX_TITLE_TOKENS:
                title = title[: MAX_TITLE_TOKENS - 3] + "..."

            # Update conversation
            conversation = await self._conversation_repository.get_by_id(conversation_id)
            if conversation:
                conversation.update_title(title)
                await self._conversation_repository.update(conversation)
        except Exception:
            # Fallback to truncated message
            fallback = first_message[:MAX_FALLBACK_TITLE_LENGTH]
            if len(first_message) > MAX_FALLBACK_TITLE_LENGTH:
                fallback += "..."
            return fallback
        else:
            return title
