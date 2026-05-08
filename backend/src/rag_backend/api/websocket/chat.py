"""WebSocket handler for streaming chat."""

import json
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.agents import build_agent_for_conversation
from rag_backend.application.services.conversation_service import ConversationService
from rag_backend.domain.models import Message, MessageRole
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.conversation_repository import (
    PostgresConversationRepository,
    PostgresMessageRepository,
)


def _sanitize_chunk(chunk: dict[str, object]) -> dict[str, object]:
    """Make an agent event chunk JSON-serializable for WebSocket.

    Deep Agents subagents may return ``ToolMessage`` or other LangChain
    message objects as the ``result`` of a ``tool_result`` event. This
    replaces any non-serializable value with its string representation.
    """
    result = chunk.get("result")
    if result is not None and not isinstance(result, str | int | float | bool | list | dict | None):
        return {**chunk, "result": str(result)}
    return chunk


class ChatWebSocketHandler:
    """Handler for WebSocket chat connections."""

    def __init__(self):
        self.active_connections: dict[UUID, WebSocket] = {}

    async def connect(
        self,
        websocket: WebSocket,
        conversation_id: UUID,
    ):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[conversation_id] = websocket

    def disconnect(self, conversation_id: UUID):
        """Remove a WebSocket connection."""
        if conversation_id in self.active_connections:
            del self.active_connections[conversation_id]

    async def handle_chat(
        self,
        websocket: WebSocket,
        conversation_id: UUID,
    ):
        """Handle WebSocket chat messages.

        This method manages the WebSocket connection and streams
        responses from the RAG agent.

        Persistence strategy:
            The user message is saved and committed *before* streaming
            starts so that the DB session has no pending changes while
            ``astream_events`` runs.  The assistant message is saved and
            committed *after* the stream ends.  This prevents SQLAlchemy
            async "Session is already flushing" errors that occur when
            tool side-effects (carousel edits, image regenerations) flush
            the same session concurrently.
        """
        container = get_container()

        from sqlalchemy.ext.asyncio import async_sessionmaker

        from rag_backend.infrastructure.database.config import c_engine

        session_maker = async_sessionmaker(
            c_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with session_maker() as db:
            try:
                # Verify conversation exists — create service directly (not via container)
                conv_repo = PostgresConversationRepository(db)
                msg_repo = PostgresMessageRepository(db)
                conversation_service = ConversationService(
                    conversation_repository=conv_repo,
                    message_repository=msg_repo,
                    max_context_tokens=4000,
                )
                conversation = await conversation_service.get_conversation(conversation_id)

                if not conversation:
                    await websocket.send_json(
                        {"type": "error", "content": f"Conversation {conversation_id} not found"}
                    )
                    await websocket.close(code=4004)
                    return

                agent = build_agent_for_conversation(conversation, db, container)

                # Handle incoming messages
                while True:
                    try:
                        # Receive message from client
                        data = await websocket.receive_text()
                        message_data = json.loads(data)

                        content = message_data.get("content", "").strip()
                        if not content:
                            await websocket.send_json(
                                {"type": "error", "content": "Message content cannot be empty"}
                            )
                            continue

                        # Persist the user message and commit BEFORE streaming
                        # so the session is clean while tools run.
                        user_message = Message(
                            role=MessageRole.USER,
                            content=content,
                            conversation_id=conversation_id,
                        )
                        await msg_repo.create(user_message)
                        await db.commit()

                        # Stream response from agent (do NOT let the agent
                        # persist messages — we handle that ourselves).
                        full_response = ""
                        async for chunk in agent.chat(
                            message=content,
                            conversation_id=conversation_id,
                            stream=True,
                            persist_messages=False,
                        ):
                            # Sanitize chunk for JSON serialization.
                            # Tool outputs from subagents may be LangChain
                            # Message objects rather than plain strings.
                            safe_chunk = _sanitize_chunk(chunk)
                            await websocket.send_json(safe_chunk)
                            if safe_chunk.get("type") == "token":
                                full_response += safe_chunk.get("content", "")

                        # Persist the assistant message and commit AFTER the
                        # stream so tool side-effects are already committed.
                        assistant_message = Message(
                            role=MessageRole.ASSISTANT,
                            content=full_response,
                            conversation_id=conversation_id,
                            sources=[],
                        )
                        await msg_repo.create(assistant_message)
                        await db.commit()

                    except json.JSONDecodeError:
                        await websocket.send_json(
                            {"type": "error", "content": "Invalid JSON format"}
                        )
                    except WebSocketDisconnect:
                        break
                    except Exception as e:
                        await websocket.send_json(
                            {"type": "error", "content": f"Error processing message: {e!s}"}
                        )

            except Exception as e:
                await websocket.send_json({"type": "error", "content": f"Connection error: {e!s}"})
                await websocket.close(code=1011)

            finally:
                self.disconnect(conversation_id)


# Global handler instance
chat_handler = ChatWebSocketHandler()
