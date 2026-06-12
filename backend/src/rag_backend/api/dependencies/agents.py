"""Per-request agent construction helpers.

The DI container's `db_session` is an async `providers.Resource`, so calling
container providers that depend on it (`rag_agent`, `carousel_refinement`,
`conversation_service`) synchronously returns an `_asyncio.Future` instead of
the actual instance. These helpers build the agents directly against a request
scoped `AsyncSession` and pull only the session-free providers (settings,
retriever, external services) from the container.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.input_sanitizer import sanitize_llm_input, sanitize_web_content
from rag_backend.agents.rag_agent import RAGAgent
from rag_backend.application.services.carousel.editorial_subagent import (
    build_editorial_carousel_subagent,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.refinement_service import (
    CarouselRefinementConfig,
    CarouselRefinementService,
)
from rag_backend.application.tools.carousel.access import (
    CarouselToolAccessContext,
    verify_carousel_tool_access,
    verify_carousel_workflow_start_access,
)
from rag_backend.application.tools.carousel.generate_carousel import (
    SubagentWorkflowStartRequest,
)
from rag_backend.domain.constants.access_control import ERR_CAROUSEL_TOOL_ACCESS_DENIED
from rag_backend.domain.constants.ai_agents import RAG_AGENT_USER_ID
from rag_backend.domain.constants.carousel_tools import (
    ERR_CAROUSEL_TOOL_INVALID_PROJECT_ID,
    ERR_CAROUSEL_TOOL_PROJECT_NOT_FOUND,
)
from rag_backend.domain.constants.carousel_workflow import SOURCE_TYPE_URL
from rag_backend.domain.constants.conversation import CONVERSATION_METADATA_PROJECT_ID
from rag_backend.domain.models import CarouselProject, Conversation
from rag_backend.domain.protocols import ResearchTool
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
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

ProjectAccessVerifier = Callable[
    [CarouselProject, CarouselToolAccessContext], str | None
]


@dataclass(frozen=True)
class RagAgentBuildContext:
    """Optional caller identity for scoped carousel tool access."""

    owner_user_id: str | None = None
    bound_project_id: str | None = None


@dataclass(frozen=True)
class AccessContext:
    """Bundled parameters for carousel project access assertions."""

    tool_access: CarouselToolAccessContext | None
    verify_access: ProjectAccessVerifier


@dataclass(frozen=True)
class WorkflowContext:
    """Bundled runtime parameters for editorial workflow execution."""

    workflow_service: EditorialWorkflowService
    workflow_user_id: str
    db: AsyncSession
    research_tool: ResearchTool | None = None


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
    if CONVERSATION_METADATA_PROJECT_ID not in conversation.metadata:
        return build_alter_ego_agent(db, container)
    if conversation.user_id is None:
        return build_alter_ego_agent(db, container)
    return build_rag_agent(
        db,
        container,
        RagAgentBuildContext(
            owner_user_id=str(conversation.user_id),
            bound_project_id=str(
                conversation.metadata[CONVERSATION_METADATA_PROJECT_ID]
            ),
        ),
    )


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


async def _assert_carousel_project_access(
    project_id: str,
    carousel_repo: PostgresCarouselRepository,
    *,
    access: AccessContext,
) -> None:
    if access.tool_access is None:
        raise ValueError(ERR_CAROUSEL_TOOL_ACCESS_DENIED)
    try:
        project_uuid = UUID(project_id)
    except ValueError as exc:
        raise ValueError(ERR_CAROUSEL_TOOL_INVALID_PROJECT_ID) from exc
    project = await carousel_repo.get_project_by_id(project_uuid)
    if project is None:
        raise ValueError(ERR_CAROUSEL_TOOL_PROJECT_NOT_FOUND)
    access_error = access.verify_access(project, access.tool_access)
    if access_error is not None:
        raise ValueError(access_error)


def _sanitize_url_sources(source_urls: list[str]) -> list[dict[str, str]]:
    return [
        {
            "title": sanitize_llm_input(url),
            "content": sanitize_llm_input(url),
            "source_type": SOURCE_TYPE_URL,
        }
        for url in source_urls
    ]


_URL_PATTERN = re.compile(r"^https?://\S+$")


async def _scrape_url_sources(
    sources: list[dict[str, str]],
    research_tool: ResearchTool | None,
) -> list[dict[str, str]]:
    """Scrape URL-type sources, replacing content with scraped text.

    Matches sources by source_type=="url" OR by content starting with
    http:// or https:// (handles RAG agent notes that embed URLs).

    Graceful degradation: if scraping fails or research_tool is None,
    the original content (URL string) is preserved.
    """
    if research_tool is None:
        return sources
    for item in sources:
        content = item.get("content", "")
        is_url = item.get("source_type") == SOURCE_TYPE_URL or bool(
            _URL_PATTERN.match(content)
        )
        if not is_url or not content:
            continue
        try:
            scraped = await research_tool.scrape_url(content)
            item["content"] = sanitize_web_content(scraped)
        except Exception as exc:
            # Graceful degradation: keep the original URL content, log for visibility.
            logger.warning("url_scrape_failed", url=content, error=str(exc))
    return sources


async def _start_editorial_workflow_for_rag(
    project_id: str,
    request: SubagentWorkflowStartRequest,
    *,
    ctx: WorkflowContext,
) -> str:
    sources = _sanitize_url_sources(request.source_urls)
    sources = await _scrape_url_sources(sources, ctx.research_tool)
    state = await ctx.workflow_service.start_workflow(
        project_id=project_id,
        workflow_input=EditorialWorkflowStartInput(
            topic=sanitize_llm_input(request.topic),
            audience=sanitize_llm_input(request.audience),
            brief=sanitize_llm_input(request.brief),
            sources=sources,
            user_id=ctx.workflow_user_id,
        ),
        db=ctx.db,
    )
    await ctx.db.commit()
    return (
        f"Phase: {state.get('current_phase', '')}; "
        f"Status: {state.get('phase_status', '')}"
    )


def build_rag_agent(
    db: AsyncSession,
    container: Container,
    context: RagAgentBuildContext | None = None,
) -> RAGAgent:
    """Build a RAGAgent bound to the given per-request session.

    Carousel-related conversations get the full agent with carousel
    tools and the carousel pipeline subagent.
    """
    build_context = context or RagAgentBuildContext()
    settings = container.settings()
    carousel_repo = PostgresCarouselRepository(db)
    carousel_refinement = CarouselRefinementService(
        CarouselRefinementConfig(
            repository=carousel_repo,
            llm_service=container.llm_service(),
            image_registry=container.image_provider_registry(),
            export_service=container.export_service(),
            pdf_slide_builder=container.pdf_slide_builder(),
            strategy_registry=container.strategy_registry(),
        )
    )
    research_tool = container.research_tool()
    llm = container.llm_service().chat_model
    workflow_service = EditorialWorkflowService(
        EditorialWorkflowConfig(
            llm=llm,
            image_registry=container.image_provider_registry(),
        ),
    )
    workflow_user_id = build_context.owner_user_id or RAG_AGENT_USER_ID
    tool_access = (
        CarouselToolAccessContext(
            owner_user_id=workflow_user_id,
            bound_project_id=build_context.bound_project_id,
        )
        if build_context.owner_user_id is not None
        else None
    )

    async def _assert_subagent_project_access(project_id: str) -> None:
        await _assert_carousel_project_access(
            project_id,
            carousel_repo,
            access=AccessContext(
                tool_access=tool_access,
                verify_access=verify_carousel_tool_access,
            ),
        )

    async def _assert_workflow_start_access(project_id: str) -> None:
        await _assert_carousel_project_access(
            project_id,
            carousel_repo,
            access=AccessContext(
                tool_access=tool_access,
                verify_access=verify_carousel_workflow_start_access,
            ),
        )

    async def start_editorial_workflow(
        project_id: str,
        request: SubagentWorkflowStartRequest,
    ) -> str:
        await _assert_workflow_start_access(project_id)
        return await _start_editorial_workflow_for_rag(
            project_id,
            request,
            ctx=WorkflowContext(
                workflow_service=workflow_service,
                workflow_user_id=workflow_user_id,
                db=db,
                research_tool=research_tool,
            ),
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
        scraped_sources = await _scrape_url_sources(sanitized_sources, research_tool)
        state = await workflow_service.start_workflow(
            project_id=project_id,
            workflow_input=EditorialWorkflowStartInput(
                topic=sanitize_llm_input(str(payload.get("topic", ""))),
                audience=sanitize_llm_input(str(payload.get("audience", ""))),
                brief=sanitize_llm_input(
                    str(payload.get("brief", payload.get("topic", "")))
                ),
                sources=scraped_sources,
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

    async def start_editorial_workflow_compat(
        project_id: str,
        request: SubagentWorkflowStartRequest,
    ) -> str:
        return await start_editorial_workflow(project_id, request)

    return RAGAgent(
        settings=settings,
        retriever=container.retriever(),
        message_repository=PostgresMessageRepository(db),
        document_repository=PostgresDocumentRepository(db),
        carousel_refinement=carousel_refinement,
        carousel_repository=carousel_repo,
        editorial_subagent=editorial_subagent,
        start_editorial_workflow=start_editorial_workflow_compat,
        carousel_tool_access=tool_access,
    )
