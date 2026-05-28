"""Per-request agent construction helpers.

The DI container's `db_session` is an async `providers.Resource`, so calling
container providers that depend on it (`rag_agent`, `carousel_refinement`,
`conversation_service`) synchronously returns an `_asyncio.Future` instead of
the actual instance. These helpers build the agents directly against a request
scoped `AsyncSession` and pull only the session-free providers (settings,
retriever, external services) from the container.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.agents.rag_agent import RAGAgent
from rag_backend.application.services.carousel.editorial_subagent import (
    build_editorial_carousel_subagent,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.refinement_service import (
    CarouselRefinementService,
)
from rag_backend.application.tools.carousel.access import (
    CarouselToolAccessContext,
    verify_carousel_tool_access,
    verify_carousel_workflow_start_access,
)
from rag_backend.domain.constants.access_control import ERR_CAROUSEL_TOOL_ACCESS_DENIED
from rag_backend.domain.constants.ai_agents import RAG_AGENT_USER_ID
from rag_backend.domain.constants.carousel_tools import (
    ERR_CAROUSEL_TOOL_INVALID_PROJECT_ID,
    ERR_CAROUSEL_TOOL_PROJECT_NOT_FOUND,
)
from rag_backend.domain.constants.carousel_workflow import SOURCE_TYPE_URL
from rag_backend.domain.constants.conversation import CONVERSATION_METADATA_PROJECT_ID
from rag_backend.domain.models import Conversation
from rag_backend.infrastructure.container import Container
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.conversation_repository import (
    PostgresMessageRepository,
)
from rag_backend.infrastructure.database.document_repository import (
    PostgresDocumentRepository,
)


def build_agent_for_conversation(
    conversation: Conversation,
    db: AsyncSession,
    container: Container,
) -> AlterEgoAgent | RAGAgent:
    """Route to the appropriate agent based on conversation metadata.

    Conversations with ``project_id`` metadata get the full RAGAgent
    (carousel tools + subagent). All others get the AlterEgoAgent
    (personal knowledge base only).
    """
    if CONVERSATION_METADATA_PROJECT_ID in conversation.metadata:
        if conversation.user_id is None:
            return build_alter_ego_agent(db, container)
        bound_project_id = str(conversation.metadata[CONVERSATION_METADATA_PROJECT_ID])
        owner_user_id = str(conversation.user_id)
        return build_rag_agent(
            db,
            container,
            owner_user_id=owner_user_id,
            bound_project_id=bound_project_id,
        )
    return build_alter_ego_agent(db, container)


def build_alter_ego_agent(db: AsyncSession, container: Container) -> AlterEgoAgent:
    """Build an AlterEgoAgent bound to the given per-request session.

    This agent is scoped to personal knowledge base search ONLY.
    It has ZERO carousel tools and cannot create or edit content.
    """
    return AlterEgoAgent(
        settings=container.settings(),
        retriever=container.retriever(),
        message_repository=PostgresMessageRepository(db),
        document_repository=PostgresDocumentRepository(db),
    )


def build_rag_agent(
    db: AsyncSession,
    container: Container,
    *,
    owner_user_id: str | None = None,
    bound_project_id: str | None = None,
) -> RAGAgent:
    """Build a RAGAgent bound to the given per-request session.

    Carousel-related conversations get the full agent with carousel
    tools and the carousel pipeline subagent.
    """
    settings = container.settings()
    carousel_repo = PostgresCarouselRepository(db)
    carousel_refinement = CarouselRefinementService(
        repository=carousel_repo,
        llm_service=container.llm_service(),
        image_registry=container.image_provider_registry(),
        export_service=container.export_service(),
        pdf_slide_builder=container.pdf_slide_builder(),
    )
    llm = container.llm_service().chat_model
    workflow_service = EditorialWorkflowService(
        llm=llm,
        image_registry=container.image_provider_registry(),
    )
    workflow_user_id = owner_user_id or RAG_AGENT_USER_ID
    tool_access = (
        CarouselToolAccessContext(
            owner_user_id=workflow_user_id,
            bound_project_id=bound_project_id,
        )
        if owner_user_id is not None
        else None
    )

    async def _assert_subagent_project_access(project_id: str) -> None:
        if tool_access is None:
            raise ValueError(ERR_CAROUSEL_TOOL_ACCESS_DENIED)
        try:
            project_uuid = UUID(project_id)
        except ValueError as exc:
            raise ValueError(ERR_CAROUSEL_TOOL_INVALID_PROJECT_ID) from exc
        project = await carousel_repo.get_project_by_id(project_uuid)
        if project is None:
            raise ValueError(ERR_CAROUSEL_TOOL_PROJECT_NOT_FOUND)
        access_error = verify_carousel_tool_access(project, tool_access)
        if access_error is not None:
            raise ValueError(access_error)

    async def _assert_workflow_start_access(project_id: str) -> None:
        if tool_access is None:
            raise ValueError(ERR_CAROUSEL_TOOL_ACCESS_DENIED)
        try:
            project_uuid = UUID(project_id)
        except ValueError as exc:
            raise ValueError(ERR_CAROUSEL_TOOL_INVALID_PROJECT_ID) from exc
        project = await carousel_repo.get_project_by_id(project_uuid)
        if project is None:
            raise ValueError(ERR_CAROUSEL_TOOL_PROJECT_NOT_FOUND)
        access_error = verify_carousel_workflow_start_access(project, tool_access)
        if access_error is not None:
            raise ValueError(access_error)

    async def start_editorial_workflow(
        project_id: str,
        topic: str,
        audience: str,
        brief: str,
        source_urls: list[str],
    ) -> str:
        await _assert_workflow_start_access(project_id)
        sources = [
            {
                "title": sanitize_llm_input(url),
                "content": sanitize_llm_input(url),
                "source_type": SOURCE_TYPE_URL,
            }
            for url in source_urls
        ]
        state = await workflow_service.start_workflow(
            project_id=project_id,
            workflow_input=EditorialWorkflowStartInput(
                topic=sanitize_llm_input(topic),
                audience=sanitize_llm_input(audience),
                brief=sanitize_llm_input(brief),
                sources=sources,
                user_id=workflow_user_id,
            ),
            db=db,
        )
        await db.commit()
        return (
            f"Phase: {state.get('current_phase', '')}; "
            f"Status: {state.get('phase_status', '')}"
        )

    async def start_from_subagent(
        project_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        await _assert_subagent_project_access(project_id)
        raw_sources = payload.get("sources", [])
        sources = raw_sources if isinstance(raw_sources, list) else []
        normalized = [
            item
            if isinstance(item, dict)
            else {"title": str(item), "content": str(item)}
            for item in sources
        ]
        sanitized_sources = [
            {
                **item,
                "title": sanitize_llm_input(str(item.get("title", ""))),
                "content": sanitize_llm_input(str(item.get("content", ""))),
            }
            for item in normalized
        ]
        state = await workflow_service.start_workflow(
            project_id=project_id,
            workflow_input=EditorialWorkflowStartInput(
                topic=sanitize_llm_input(str(payload.get("topic", ""))),
                audience=sanitize_llm_input(str(payload.get("audience", ""))),
                brief=sanitize_llm_input(
                    str(payload.get("brief", payload.get("topic", "")))
                ),
                sources=sanitized_sources,
                user_id=workflow_user_id,
            ),
            db=db,
        )
        await db.commit()
        return dict(state)

    editorial_subagent = (
        build_editorial_carousel_subagent(start_from_subagent)
        if tool_access is not None
        else None
    )
    return RAGAgent(
        settings=settings,
        retriever=container.retriever(),
        message_repository=PostgresMessageRepository(db),
        document_repository=PostgresDocumentRepository(db),
        carousel_refinement=carousel_refinement,
        carousel_repository=carousel_repo,
        editorial_subagent=editorial_subagent,
        start_editorial_workflow=start_editorial_workflow,
        carousel_tool_access=tool_access,
    )
