"""Conversation API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    ErrorResponse,
    MessageListResponse,
    MessageResponse,
    MessageSource,
)
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.database.conversation_repository import (
    PostgresConversationRepository,
    PostgresMessageRepository,
)
from rag_backend.application.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


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
    db: AsyncSession = Depends(get_session),
):
    """Create a new conversation."""
    service = _make_conversation_service(db)

    conversation = await service.create_conversation(
        title=request.title,
        metadata=request.metadata,
    )
    await db.commit()

    return conversation


@router.get(
    "",
    response_model=ConversationListResponse,
    responses={
        200: {"description": "List of conversations"},
    },
)
async def list_conversations(
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    db: AsyncSession = Depends(get_session),
):
    """List all conversations."""
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
        404: {"model": ErrorResponse, "description": "Conversation not found"},
    },
)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_session),
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
        404: {"model": ErrorResponse, "description": "Conversation not found"},
    },
)
async def get_conversation_messages(
    conversation_id: UUID,
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    db: AsyncSession = Depends(get_session),
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
        404: {"model": ErrorResponse, "description": "Conversation not found"},
    },
)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_session),
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

    return None


@router.post(
    "/{conversation_id}/generate-title",
    response_model=ConversationResponse,
    responses={
        200: {"description": "Title generated successfully"},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
    },
)
async def generate_conversation_title(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_session),
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

    updated_conversation = await service.get_conversation(conversation_id)
    return updated_conversation


@router.post(
    "/{conversation_id}/chat",
    response_model=ChatResponse,
    responses={
        200: {"description": "Chat response with sources"},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def chat(
    conversation_id: UUID,
    body: ChatRequest,
    db: AsyncSession = Depends(get_session),
):
    """Send a chat message and get a non-streaming response with sources."""
    container = get_container()
    service = _make_conversation_service(db)

    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with id {conversation_id} not found",
        )

    rag_agent = container.rag_agent()
    sources = []
    full_response = ""

    async for event in rag_agent.chat(
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

    return ChatResponse(
        content=full_response,
        sources=formatted_sources,
        conversation_id=conversation_id,
    )
