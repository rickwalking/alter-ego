"""Conversation API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    ERR_CONVERSATION_NOT_FOUND,
    ERR_FORBIDDEN,
    ERR_NOT_AUTHENTICATED,
)
from rag_backend.api.dependencies import (
    get_optional_user,
    require_authenticated_user,
)
from rag_backend.api.dependencies.agents import build_agent_for_conversation
from rag_backend.api.dependencies.carousel_access import (
    assert_carousel_conversation_chat_access,
    validate_carousel_conversation_metadata,
)
from rag_backend.api.dependencies.resource_access import assert_conversation_access
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
from rag_backend.domain.constants.conversation import (
    CONVERSATION_METADATA_PROJECT_ID,
)
from rag_backend.domain.models import User
from rag_backend.infrastructure.auth import create_anonymous_token
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.database.conversation_repository import (
    PostgresConversationRepository,
    PostgresMessageRepository,
)
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/conversations", tags=["conversations"])

_AGENT_ORIGIN_ALTER_EGO = "alter-ego"
_AGENT_ORIGIN_RAG = "rag-agent"

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
@router.post(
    "/",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_conversation(
    body: ConversationCreate,
    http_request: Request,
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

    auth_header = http_request.headers.get("authorization", "")
    cookie_keys = list(http_request.cookies.keys())
    logger.info(
        "create_conversation_called",
        is_authenticated=user is not None,
        has_auth_header=bool(auth_header),
        cookie_keys=cookie_keys,
        content_length=http_request.headers.get("content-length"),
    )

    service = _make_conversation_service(db)

    await validate_carousel_conversation_metadata(db, body.metadata, user)

    conversation = await service.create_conversation(
        title=body.title,
        metadata=body.metadata,
        user_id=user.id if user else None,
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
@router.get(
    "/",
    response_model=ConversationListResponse,
    include_in_schema=False,
)
async def list_conversations(
    user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[
        int, Query(ge=1, le=100, description="Number of items to return")
    ] = 20,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    origin: Annotated[
        str | None,
        Query(description="Filter by agent origin (e.g. alter_ego)"),
    ] = None,
    db: AsyncSession = Depends(get_session),
):
    """List conversations owned by the authenticated user."""
    service = _make_conversation_service(db)

    conversations = await service.list_conversations(
        limit=limit,
        offset=offset,
        user_id=user.id,
        origin=origin,
    )
    total = await service.count_conversations_for_user(user.id, origin=origin)

    return {
        "items": conversations,
        "total": total,
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
    user: Annotated[User, Depends(require_authenticated_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Get a single conversation by ID."""
    service = _make_conversation_service(db)

    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_CONVERSATION_NOT_FOUND,
        )

    assert_conversation_access(conversation, user)
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
    user: Annotated[User, Depends(require_authenticated_user)],
    limit: Annotated[
        int, Query(ge=1, le=100, description="Number of messages to return")
    ] = 50,
    db: AsyncSession = Depends(get_session),
):
    """Get all messages for a conversation."""
    service = _make_conversation_service(db)

    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_CONVERSATION_NOT_FOUND,
        )

    assert_conversation_access(conversation, user)
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
    user: Annotated[User, Depends(require_authenticated_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Delete a conversation and all its messages."""
    service = _make_conversation_service(db)

    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_CONVERSATION_NOT_FOUND,
        )

    assert_conversation_access(conversation, user)
    success = await service.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_CONVERSATION_NOT_FOUND,
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
    user: Annotated[User, Depends(require_authenticated_user)],
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
            detail=ERR_CONVERSATION_NOT_FOUND,
        )

    assert_conversation_access(conversation, user)

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
    request: Request,
    response: Response,
    user: Annotated[User | None, Depends(get_optional_user)] = None,
    db: Annotated[AsyncSession, Depends(get_session)] = None,
) -> ChatResponse:
    """Send a chat message and get a non-streaming response with sources."""
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

    if user is not None and conversation.user_id is not None:
        assert_conversation_access(conversation, user)

    assert_carousel_conversation_chat_access(conversation, user)

    msg_repo = PostgresMessageRepository(db)
    msg_count = await msg_repo.count_by_conversation(conversation_id)
    _check_conversation_limit(msg_count)

    agent = build_agent_for_conversation(conversation, db, container)
    agent_origin = (
        _AGENT_ORIGIN_RAG
        if CONVERSATION_METADATA_PROJECT_ID in conversation.metadata
        else _AGENT_ORIGIN_ALTER_EGO
    )

    sources: list[dict[str, object]] = []
    full_response = ""

    async for event in agent.chat(
        message=body.content,
        conversation_id=conversation_id,
        stream=False,
    ):
        if event["type"] == "complete":
            full_response = str(event["content"])
        elif event["type"] == "sources":
            sources = list(event["content"])

    formatted_sources = [
        MessageSource(
            document_id=str(src.get("document_id", "")),
            document_title=str(src.get("document_title", "")),
            content=str(src.get("content", "")),
            score=float(src.get("score", 0.0)),
        )
        for src in sources
        if isinstance(src, dict)
    ]

    response.headers["X-Agent-Origin"] = agent_origin
    return ChatResponse(
        content=full_response,
        sources=formatted_sources,
        conversation_id=conversation_id,
    )
