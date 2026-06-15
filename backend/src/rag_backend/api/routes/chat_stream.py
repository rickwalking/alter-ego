"""SSE streaming endpoints for chat — thin HTTP adapters over the facade.

Provides two dedicated endpoints:

* ``POST /conversations/{id}/chat/stream`` — Alter-Ego public chat (no auth).
* ``POST /conversations/{id}/publish-chat/stream`` — Carousel agent chat (auth required).

Both return ``text/event-stream`` responses with incremental event IDs for
``Last-Event-ID`` resumability. The endpoints parse the request, run the
edge-level access/limit checks, and delegate the SSE stream to the conversation
module's ``ConversationStreamHandler`` (resolved via ``get_conversation_stream_handler``
at the edge). Agent construction routes through the request-scoped
``ChatAgentFactory`` adapter and the module-level builder seam below, so the SSE
event types/order, ``id:``/``data:`` framing, keep-alive cadence, ``Last-Event-ID``
resume, the ``metadata.project_id`` AlterEgo/RAG routing, and the AE-0093
knowledge-facade wiring stay byte-identical (AE-0102). The persist/commit of chat
messages is owned by the streaming service the runner wraps; this route never
calls ``db.commit()``.

The module-level ``build_alter_ego_agent`` / ``build_rag_agent`` names are the
ACTUAL functions the streaming path calls (via the route-local agent builders),
so the AE-0097 safety net's monkeypatch keeps overriding agent construction
without a live LLM/Pinecone.
"""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.rag_agent import RAGAgent
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
    RagAgentBuildContext,
    build_alter_ego_agent,
    build_rag_agent,
)
from rag_backend.api.dependencies.carousel_access import (
    assert_carousel_conversation_chat_access,
)
from rag_backend.api.dependencies.conversation import (
    get_conversation_stream_handler,
    get_legacy_chat_agent_factory,
)
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas import ChatRequest, ErrorResponse
from rag_backend.application.services.conversation_service import ConversationService
from rag_backend.domain.constants.conversation import CONVERSATION_METADATA_PROJECT_ID
from rag_backend.domain.models import User
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.database.conversation_repository import (
    PostgresConversationRepository,
    PostgresMessageRepository,
)
from rag_backend.modules.conversation import (
    Conversation,
    ConversationStreamHandler,
    LegacyChatAgentFactory,
    StreamChatCommand,
)

router = APIRouter(prefix="/conversations", tags=["chat-stream"])

_MAX_MESSAGES_PER_CONVERSATION = 20


class _AlterEgoAgentBuilder:
    """Route-local ``ChatAgentBuilder`` for the public Alter-Ego stream.

    Reuses the DI-built factory's bound session + container and routes
    construction through THIS module's ``build_alter_ego_agent`` name so the
    AE-0097 safety net (which monkeypatches it) keeps overriding agent
    construction without a live LLM — the knowledge-facade wiring stays identical.
    """

    def __init__(self, factory: LegacyChatAgentFactory) -> None:
        self._db = factory.session
        self._container = factory.container

    def build(self) -> AlterEgoAgent | RAGAgent:
        return build_alter_ego_agent(self._db, self._container)


class _RagAgentBuilder:
    """Route-local ``ChatAgentBuilder`` for the carousel publish-chat stream.

    Reuses the DI-built factory's bound session + container and routes
    construction through THIS module's ``build_rag_agent`` name (monkeypatch
    seam), bound to the conversation owner + project so the ``metadata.project_id``
    RAG routing and the knowledge-facade wiring stay identical.
    """

    def __init__(
        self, factory: LegacyChatAgentFactory, context: RagAgentBuildContext
    ) -> None:
        self._db = factory.session
        self._container = factory.container
        self._context = context

    def build(self) -> AlterEgoAgent | RAGAgent:
        return build_rag_agent(self._db, self._container, self._context)


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


async def _enforce_message_cap(db: AsyncSession, conversation_id: UUID) -> None:
    """Enforce the per-conversation message cap (429 before the stream starts)."""
    msg_repo = PostgresMessageRepository(db)
    msg_count = await msg_repo.count_by_conversation(conversation_id)
    _check_conversation_limit(msg_count)


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
    handler: Annotated[
        ConversationStreamHandler | None, Depends(get_conversation_stream_handler)
    ] = None,
    agent_factory: Annotated[
        LegacyChatAgentFactory | None, Depends(get_legacy_chat_agent_factory)
    ] = None,
) -> StreamingResponse:
    """Send a message to the Alter-Ego agent and stream the response via SSE.

    No authentication required. Conversations are ephemeral — each page
    refresh creates a fresh session. No cookies or localStorage are used.
    """
    if db is None or handler is None or agent_factory is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session not resolved",
        )

    await _enforce_message_cap(db, conversation_id)

    command = StreamChatCommand(
        conversation_id=conversation_id,
        content=body.content,
        last_event_id=_parse_last_event_id(request),
    )
    agent_builder = _AlterEgoAgentBuilder(agent_factory)

    async def event_generator() -> AsyncIterator[str]:
        async for event in handler.stream(command, agent_builder):
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
    handler: Annotated[
        ConversationStreamHandler | None, Depends(get_conversation_stream_handler)
    ] = None,
    agent_factory: Annotated[
        LegacyChatAgentFactory | None, Depends(get_legacy_chat_agent_factory)
    ] = None,
) -> StreamingResponse:
    """Send a message to the carousel RAG agent and stream the response via SSE.

    Authentication is required. The conversation must have ``project_id``
    metadata linking it to a carousel project.
    """
    if db is None or handler is None or agent_factory is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session not resolved",
        )

    conversation = await _load_carousel_conversation(db, conversation_id, user)
    await _enforce_message_cap(db, conversation_id)

    command = StreamChatCommand(
        conversation_id=conversation_id,
        content=body.content,
        last_event_id=_parse_last_event_id(request),
    )
    agent_builder = _RagAgentBuilder(
        agent_factory,
        RagAgentBuildContext(
            owner_user_id=str(user.id),
            bound_project_id=str(
                conversation.metadata[CONVERSATION_METADATA_PROJECT_ID]
            ),
        ),
    )

    async def event_generator() -> AsyncIterator[str]:
        async for event in handler.stream(command, agent_builder):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type=MEDIA_TYPE_STREAM,
        headers={"Cache-Control": "no-cache"},
    )


async def _load_carousel_conversation(
    db: AsyncSession,
    conversation_id: UUID,
    user: User,
) -> Conversation:
    """Load + access-check a carousel-bound conversation (404/403/400 order)."""
    service = _make_conversation_service(db)
    conversation = await service.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_CONVERSATION_NOT_FOUND,
        )
    assert_carousel_conversation_chat_access(conversation, user)
    if CONVERSATION_METADATA_PROJECT_ID not in conversation.metadata:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_NOT_CAROUSEL_CONVERSATION,
        )
    return conversation
