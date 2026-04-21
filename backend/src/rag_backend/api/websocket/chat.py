"""WebSocket handler for streaming chat."""

import json
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.agents import build_rag_agent
from rag_backend.application.services.conversation_service import ConversationService
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.conversation_repository import (
    PostgresConversationRepository,
    PostgresMessageRepository,
)


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
                conversation = await conversation_service.get_conversation(
                    conversation_id
                )

                if not conversation:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Conversation {conversation_id} not found"
                    })
                    await websocket.close(code=4004)
                    return

                agent = build_rag_agent(db, container)

                # Handle incoming messages
                while True:
                    try:
                        # Receive message from client
                        data = await websocket.receive_text()
                        message_data = json.loads(data)

                        content = message_data.get("content", "").strip()
                        if not content:
                            await websocket.send_json({
                                "type": "error",
                                "content": "Message content cannot be empty"
                            })
                            continue

                        # Stream response from agent
                        async for chunk in agent.chat(
                            message=content,
                            conversation_id=conversation_id,
                            stream=True,
                        ):
                            await websocket.send_json(chunk)

                    except json.JSONDecodeError:
                        await websocket.send_json({
                            "type": "error",
                            "content": "Invalid JSON format"
                        })
                    except WebSocketDisconnect:
                        break
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "content": f"Error processing message: {str(e)}"
                        })

            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Connection error: {str(e)}"
                })
                await websocket.close(code=1011)

            finally:
                self.disconnect(conversation_id)


# Global handler instance
chat_handler = ChatWebSocketHandler()
