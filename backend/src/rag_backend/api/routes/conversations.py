"""Conversation API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import ERR_FORBIDDEN, ERR_NOT_AUTHENTICATED
from rag_backend.api.dependencies import (
    get_optional_user,
    require_authenticated_user,
)
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    ErrorResponse,
    MessageListResponse,
    MessageSource,
)
from rag_backend.application.services.conversation_service import ConversationService
from rag_backend.domain.models import User
from rag_backend.infrastructure.auth import create_anonymous_token
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.database.conversation_repository import (
    PostgresConversationRepository,
    PostgresMessageRepository,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])

_MAX_MESSAGES_PER_CONVERSATION = 20


def _get_limit_key(user: User | None) -> str:
    """Return a rate-limit key based on user id or IP."""
    if user is not None:
        return f"user:{user.id}"
    return "ip"


def _check_conversation_limit(message_count: int) -> None:
    """Raise 429 if the conversation has reached the message cap."""
    if message_count >= _MAX_MESSAGES_PER_CONVERSATION:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Conversation limit reached. Start a new chat.",
        )


def _make_conversation_service(db: AsyncSession) -> ConversationService:
    conv_repo = PostgresConversationRepository(db)
    msg_repo = PostgresMessageRepository(db)
    return ConversationService(conv_repo, msg_repo, max_context_tokens=4000)


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Conversation created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
    },
)
async def create_conversation(
    request: ConversationCreate,
    response: Response,
    user: Annotated[User | None, Depends(get_optional_user)] = None,
    db: Annotated[AsyncSession, Depends(get_session)] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
):
    """Create a new conversation.

    Authenticated users get a persistent conversation.
    Anonymous visitors get an ephemeral conversation with a temporary token.
    """
    if db is None or settings is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dependencies not resolved",
        )

    service = _make_conversation_service(db)

    conversation = await service.create_conversation(
        title=request.title,
        metadata=request.metadata,
    )
    await db.commit()

    # If anonymous, generate a token
    if user is None:
        anon_token = create_anonymous_token(settings, str(conversation.id))
        response.set_cookie(
            key="anon_token",
            value=anon_token,
            httponly=True,
            secure=not settings.debug,
            samesite="strict",
            max_age=settings.anon_token_expire_minutes * 60,
        )

    return conversation


@router.get(
    "",
    response_model=ConversationListResponse,
    responses={
        200: {"description": "List of conversations"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
    },
)
async def list_conversations(
    _user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100, description="Number of items to return")] = 20,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    db: AsyncSession = Depends(get_session),  # noqa: FAST002
):
    """List all conversations for the authenticated user."""
    service = _make_conversation_service(db)

    conversations = await service.list_conversations(limit=limit, offset=offset)

    return {
        "items": conversations,
        "total": len(conversations),
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    responses={
        200: {"description": "Conversation found"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        403: {"model": ErrorResponse, "description": ERR_FORBIDDEN},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
    },
)
async def get_conversation(
    conversation_id: UUID,
    _user: Annotated[User, Depends(require_authenticated_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Get a single conversation by ID."""
    service = _make_conversation_service(db)

    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with id {conversation_id} not found",
        )

    return conversation


@router.get(
    "/{conversation_id}/messages",
    response_model=MessageListResponse,
    responses={
        200: {"description": "List of messages"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        403: {"model": ErrorResponse, "description": ERR_FORBIDDEN},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
    },
)
async def get_conversation_messages(
    conversation_id: UUID,
    _user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100, description="Number of messages to return")] = 50,
    db: AsyncSession = Depends(get_session),  # noqa: FAST002
):
    """Get all messages for a conversation."""
    service = _make_conversation_service(db)

    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with id {conversation_id} not found",
        )

    messages = await service.get_conversation_history(conversation_id, limit=limit)

    return {
        "items": messages,
        "conversation_id": conversation_id,
    }


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Conversation deleted successfully"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        403: {"model": ErrorResponse, "description": ERR_FORBIDDEN},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
    },
)
async def delete_conversation(
    conversation_id: UUID,
    _user: Annotated[User, Depends(require_authenticated_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Delete a conversation and all its messages."""
    service = _make_conversation_service(db)

    success = await service.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with id {conversation_id} not found",
        )
    await db.commit()


@router.post(
    "/{conversation_id}/generate-title",
    response_model=ConversationResponse,
    responses={
        200: {"description": "Title generated successfully"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        403: {"model": ErrorResponse, "description": ERR_FORBIDDEN},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
    },
)
async def generate_conversation_title(
    conversation_id: UUID,
    _user: Annotated[User, Depends(require_authenticated_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Generate a title for the conversation based on the first message."""
    container = get_container()
    service = _make_conversation_service(db)
    llm_service = container.llm_service()

    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with id {conversation_id} not found",
        )

    await service.generate_title(
        conversation_id=conversation_id,
        llm_generate_func=llm_service.generate,
    )
    await db.commit()

    return await service.get_conversation(conversation_id)


@router.post(
    "/{conversation_id}/chat",
    response_model=ChatResponse,
    responses={
        200: {"description": "Chat response with sources"},
        401: {"model": ErrorResponse, "description": ERR_NOT_AUTHENTICATED},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("10/minute")
async def chat(
    conversation_id: UUID,
    body: ChatRequest,
    _request: Request,
    response: Response,
    _user: Annotated[User | None, Depends(get_optional_user)] = None,
    db: Annotated[AsyncSession, Depends(get_session)] = None,
):
    """Send a chat message and get a non-streaming response with sources.

    Accessible to both authenticated users and anonymous visitors.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session not resolved",
        )

    container = get_container()
    service = _make_conversation_service(db)

    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with id {conversation_id} not found",
        )

    # Enforce per-conversation message limit
    msg_repo = PostgresMessageRepository(db)
    msg_count = await msg_repo.count_by_conversation(conversation_id)
    _check_conversation_limit(msg_count)

    from rag_backend.agents.rag_agent import RAGAgent
    from rag_backend.api.dependencies.agents import build_agent_for_conversation

    agent = build_agent_for_conversation(conversation, db, container)
    agent_origin = "rag-agent" if isinstance(agent, RAGAgent) else "alter-ego"
    response.headers["X-Agent-Origin"] = agent_origin
    sources = []
    full_response = ""

    async for event in agent.chat(
        message=body.content,
        conversation_id=conversation_id,
        stream=False,
    ):
        if event["type"] == "complete":
            full_response = event["content"]
        elif event["type"] == "sources":
            sources = event["content"]

    formatted_sources = []
    for src in sources:
        if isinstance(src, dict):
            formatted_sources.append(
                MessageSource(
                    document_id=src.get("document_id", ""),
                    document_title=src.get("document_title", ""),
                    content=src.get("content", ""),
                    score=src.get("score", 0.0),
                )
            )

    response.headers["X-Agent-Origin"] = agent_origin
    return ChatResponse(
        content=full_response,
        sources=formatted_sources,
        conversation_id=conversation_id,
    )
