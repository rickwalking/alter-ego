"""Conversation API routes — thin HTTP adapters over the conversation facade.

Each ``/api/conversations`` endpoint parses the request into a conversation
command/query, delegates to the request-scoped handlers (resolved via the
``get_conversation_handlers`` DI provider at the edge — never the global DI
container here), and maps the returned domain entity/result onto the HTTP
response. Writes commit through the module's Unit of Work (the single commit
owner); these routes never call ``db.commit()`` (AE-0101). The anon_token
Set-Cookie attributes, the ``X-Agent-Origin`` header, rate limits, access checks
(shared ``resource_access`` / ``carousel_access``), status codes, and response
shapes stay byte-identical. Non-stream chat only — SSE stays in chat_stream.py.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.rag_agent import RAGAgent
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
from rag_backend.api.dependencies.conversation import (
    get_conversation_handlers,
    get_conversation_module,
    get_conversation_title_generator,
    get_legacy_chat_agent_factory,
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
from rag_backend.domain.models import User
from rag_backend.infrastructure.auth import create_anonymous_token
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.logging import get_logger
from rag_backend.modules.conversation import (
    ChatCommand,
    Conversation,
    ConversationHandlers,
    ConversationLimitReachedError,
    ConversationModule,
    CreateConversationCommand,
    DeleteConversationCommand,
    GenerateTitleCommand,
    GetConversationQuery,
    GetMessagesQuery,
    LegacyChatAgentFactory,
    ListConversationsQuery,
    LlmGenerate,
)

logger = get_logger()

router = APIRouter(prefix="/conversations", tags=["conversations"])

_DEPENDENCIES_NOT_RESOLVED = "Dependencies not resolved"
_DB_NOT_RESOLVED = "Database session not resolved"
_CHAT_LIMIT_DETAIL = "Conversation limit reached. Start a new chat."
_CHAT_NOT_FOUND_DETAIL = "Conversation with id {conversation_id} not found"


class _RouteChatAgentFactory:
    """Route-local ``ChatAgentFactory`` bound to the patchable builder seam.

    Delegates to THIS module's ``build_agent_for_conversation`` name so the
    AE-0097 safety net (which monkeypatches it) keeps overriding agent
    construction without a live LLM, while reusing the request session +
    container from the DI-built factory — routing + wiring stay byte-identical.
    """

    def __init__(self, factory: LegacyChatAgentFactory) -> None:
        self._db = factory.session
        self._container = factory.container

    def build_for_conversation(
        self, conversation: Conversation
    ) -> AlterEgoAgent | RAGAgent:
        return build_agent_for_conversation(conversation, self._db, self._container)


async def _load_owned_conversation(
    handlers: ConversationHandlers,
    conversation_id: UUID,
    user: User,
) -> Conversation:
    """Load a conversation (404 if missing), then assert the caller owns it.

    Preserves the legacy 404-before-403 ordering + ``ERR_CONVERSATION_NOT_FOUND``.
    """
    conversation = await handlers.get(GetConversationQuery(conversation_id))
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_CONVERSATION_NOT_FOUND,
        )
    assert_conversation_access(conversation, user)
    return conversation


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
    handlers: Annotated[
        ConversationHandlers | None, Depends(get_conversation_handlers)
    ] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
    db: Annotated[AsyncSession, Depends(get_session)] = None,
):
    """Create a conversation (persistent if authenticated; anon gets a token)."""
    if handlers is None or settings is None or db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_DEPENDENCIES_NOT_RESOLVED,
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

    await validate_carousel_conversation_metadata(db, body.metadata, user)

    conversation = await handlers.create(
        CreateConversationCommand(
            title=body.title,
            metadata=body.metadata,
            user_id=user.id if user else None,
        )
    )

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
    handlers: Annotated[ConversationHandlers, Depends(get_conversation_handlers)],
    limit: Annotated[
        int, Query(ge=1, le=100, description="Number of items to return")
    ] = 20,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    origin: Annotated[
        str | None,
        Query(description="Filter by agent origin (e.g. alter_ego)"),
    ] = None,
):
    """List conversations owned by the authenticated user."""
    page = await handlers.list_for_owner(
        ListConversationsQuery(
            user_id=user.id, limit=limit, offset=offset, origin=origin
        )
    )
    return {
        "items": page.items,
        "total": page.total,
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
    handlers: Annotated[ConversationHandlers, Depends(get_conversation_handlers)],
):
    """Get a single conversation by ID."""
    return await _load_owned_conversation(handlers, conversation_id, user)


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
    handlers: Annotated[ConversationHandlers, Depends(get_conversation_handlers)],
    limit: Annotated[
        int, Query(ge=1, le=100, description="Number of messages to return")
    ] = 50,
):
    """Get all messages for a conversation."""
    await _load_owned_conversation(handlers, conversation_id, user)
    messages = await handlers.get_messages(
        GetMessagesQuery(conversation_id=conversation_id, limit=limit)
    )
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
    handlers: Annotated[ConversationHandlers, Depends(get_conversation_handlers)],
):
    """Delete a conversation and all its messages."""
    await _load_owned_conversation(handlers, conversation_id, user)
    success = await handlers.delete(DeleteConversationCommand(conversation_id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_CONVERSATION_NOT_FOUND,
        )


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
    handlers: Annotated[ConversationHandlers, Depends(get_conversation_handlers)],
    llm_generate: Annotated[LlmGenerate, Depends(get_conversation_title_generator)],
):
    """Generate a title for the conversation based on the first message."""
    await _load_owned_conversation(handlers, conversation_id, user)
    return await handlers.generate_title(
        GenerateTitleCommand(conversation_id), llm_generate
    )


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
    module: Annotated[
        ConversationModule | None, Depends(get_conversation_module)
    ] = None,
    agent_factory: Annotated[
        LegacyChatAgentFactory | None, Depends(get_legacy_chat_agent_factory)
    ] = None,
) -> ChatResponse:
    """Send a chat message and get a non-streaming response with sources."""
    if module is None or agent_factory is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_DB_NOT_RESOLVED,
        )

    handlers = ConversationHandlers(
        service=module.service,
        agent_factory=_RouteChatAgentFactory(agent_factory),
        unit_of_work=module.unit_of_work,
    )

    conversation = await handlers.get(GetConversationQuery(conversation_id))
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_CHAT_NOT_FOUND_DETAIL.format(conversation_id=conversation_id),
        )

    if user is not None and conversation.user_id is not None:
        assert_conversation_access(conversation, user)

    assert_carousel_conversation_chat_access(conversation, user)

    try:
        result = await handlers.chat(
            ChatCommand(conversation_id=conversation_id, content=body.content),
            conversation,
        )
    except ConversationLimitReachedError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=_CHAT_LIMIT_DETAIL,
        ) from None

    response.headers["X-Agent-Origin"] = result.agent_origin
    sources = [
        MessageSource(
            document_id=src.document_id,
            document_title=src.document_title,
            content=src.content,
            score=src.score,
        )
        for src in result.sources
    ]
    return ChatResponse(
        content=result.content, sources=sources, conversation_id=conversation_id
    )
