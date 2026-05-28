"""SSE streaming endpoints for chat.

Provides two dedicated endpoints:

* ``POST /conversations/{id}/chat/stream`` — Alter-Ego public chat (no auth).
* ``POST /conversations/{id}/publish-chat/stream`` — Carousel agent chat (auth required).

Both return ``text/event-stream`` responses with incremental event IDs
for ``Last-Event-ID`` resumability.
"""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    ERR_CONVERSATION_NOT_FOUND,
    ERR_NOT_AUTHENTICATED,
    ERR_NOT_CAROUSEL_CONVERSATION,
    ERR_NOT_FOUND,
    MEDIA_TYPE_STREAM,
)
from rag_backend.api.dependencies import (
    require_authenticated_user,
)
from rag_backend.api.dependencies.agents import (
    build_alter_ego_agent,
    build_rag_agent,
)
from rag_backend.api.dependencies.carousel_access import (
    assert_carousel_conversation_chat_access,
)
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas import ChatRequest, ErrorResponse
from rag_backend.application.services.chat_stream_service import stream_chat_response
from rag_backend.application.services.conversation_service import ConversationService
from rag_backend.domain.constants.conversation import CONVERSATION_METADATA_PROJECT_ID
from rag_backend.domain.models import User
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.database.conversation_repository import (
    PostgresConversationRepository,
    PostgresMessageRepository,
)

router = APIRouter(prefix="/conversations", tags=["chat-stream"])

_MAX_MESSAGES_PER_CONVERSATION = 20


def _check_conversation_limit(message_count: int) -> None:
    """Raise 429 if the conversation has reached the message cap."""
    if message_count >= _MAX_MESSAGES_PER_CONVERSATION:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Conversation limit reached. Start a new chat.",
        )


def _make_conversation_service(db: AsyncSession) -> ConversationService:
    """Factory for a request-scoped ConversationService."""
    conv_repo = PostgresConversationRepository(db)
    msg_repo = PostgresMessageRepository(db)
    return ConversationService(conv_repo, msg_repo, max_context_tokens=4000)


def _parse_last_event_id(request: Request) -> int | None:
    """Extract ``Last-Event-ID`` from request headers if present."""
    raw = request.headers.get("last-event-id")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


@router.post(
    "/{conversation_id}/chat/stream",
    responses={
        200: {"description": "SSE stream of chat tokens"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        404: {"model": ErrorResponse, "description": ERR_NOT_FOUND},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("10/minute")
async def chat_stream(
    conversation_id: UUID,
    body: ChatRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)] = None,
) -> StreamingResponse:
    """Send a message to the Alter-Ego agent and stream the response via SSE.

    No authentication required. Conversations are ephemeral — each page
    refresh creates a fresh session. No cookies or localStorage are used.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session not resolved",
        )

    # Enforce per-conversation message limit
    msg_repo = PostgresMessageRepository(db)
    msg_count = await msg_repo.count_by_conversation(conversation_id)
    _check_conversation_limit(msg_count)

    last_event_id = _parse_last_event_id(request)

    async def event_generator() -> AsyncIterator[str]:
        async for event in stream_chat_response(
            conversation_id=conversation_id,
            content=body.content,
            db=db,
            agent_builder=lambda: build_alter_ego_agent(db, get_container()),
            last_event_id=last_event_id,
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type=MEDIA_TYPE_STREAM,
        headers={"Cache-Control": "no-cache"},
    )


@router.post(
    "/{conversation_id}/publish-chat/stream",
    responses={
        200: {"description": "SSE stream of carousel agent tokens"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": ERR_NOT_FOUND},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("10/minute")
async def publish_chat_stream(
    conversation_id: UUID,
    body: ChatRequest,
    request: Request,
    user: Annotated[User, Depends(require_authenticated_user)],
    db: Annotated[AsyncSession, Depends(get_session)] = None,
) -> StreamingResponse:
    """Send a message to the carousel RAG agent and stream the response via SSE.

    Authentication is required. The conversation must have ``project_id``
    metadata linking it to a carousel project.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session not resolved",
        )

    service = _make_conversation_service(db)
    conversation = await service.get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_CONVERSATION_NOT_FOUND,
        )

    # Enforce conversation ownership for carousel publish chat
    assert_carousel_conversation_chat_access(conversation, user)

    if CONVERSATION_METADATA_PROJECT_ID not in conversation.metadata:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_NOT_CAROUSEL_CONVERSATION,
        )

    # Enforce per-conversation message limit
    msg_repo = PostgresMessageRepository(db)
    msg_count = await msg_repo.count_by_conversation(conversation_id)
    _check_conversation_limit(msg_count)

    last_event_id = _parse_last_event_id(request)

    async def event_generator() -> AsyncIterator[str]:
        async for event in stream_chat_response(
            conversation_id=conversation_id,
            content=body.content,
            db=db,
            agent_builder=lambda: build_rag_agent(
                db,
                get_container(),
                owner_user_id=str(user.id),
                bound_project_id=str(
                    conversation.metadata[CONVERSATION_METADATA_PROJECT_ID]
                ),
            ),
            last_event_id=last_event_id,
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type=MEDIA_TYPE_STREAM,
        headers={"Cache-Control": "no-cache"},
    )
