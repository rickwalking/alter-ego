"""Per-request agent construction helpers.

The DI container's `db_session` is an async `providers.Resource`, so calling
container providers that depend on it (`rag_agent`, `carousel_agent`,
`conversation_service`) synchronously returns an `_asyncio.Future` instead of
the actual instance. These helpers build the agents directly against a request
scoped `AsyncSession` and pull only the session-free providers (settings,
retriever, external services) from the container.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.alter_ego_agent import AlterEgoAgent
from rag_backend.agents.carousel_orchestrator import CarouselAgent
from rag_backend.agents.rag_agent import RAGAgent
from rag_backend.domain.models import Conversation
from rag_backend.infrastructure.container import Container
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.infrastructure.database.conversation_repository import (
    PostgresMessageRepository,
)
from rag_backend.infrastructure.database.document_repository import (
    PostgresDocumentRepository,
)

CONVERSATION_METADATA_PROJECT_ID = "project_id"


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
        return build_rag_agent(db, container)
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


def build_rag_agent(db: AsyncSession, container: Container) -> RAGAgent:
    """Build a RAGAgent bound to the given per-request session.

    Carousel-related conversations get the full agent with carousel
    tools and the carousel pipeline subagent.
    """
    settings = container.settings()
    carousel_repo = PostgresCarouselRepository(db)
    carousel_agent = CarouselAgent(
        repository=carousel_repo,
        llm_service=container.llm_service(),
        research_tool=container.research_tool(),
        image_registry=container.image_provider_registry(),
        export_service=container.export_service(),
        linkedin_post_generator=container.linkedin_post_generator(),
        pdf_slide_builder=container.pdf_slide_builder(),
        output_base_dir=settings.carousel_output_dir,
        session_maker=get_session_maker(),
        repository_factory=PostgresCarouselRepository,
    )
    return RAGAgent(
        settings=settings,
        retriever=container.retriever(),
        message_repository=PostgresMessageRepository(db),
        document_repository=PostgresDocumentRepository(db),
        carousel_agent=carousel_agent,
        carousel_repository=carousel_repo,
    )
