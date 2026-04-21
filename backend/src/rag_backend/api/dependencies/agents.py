"""Per-request agent construction helpers.

The DI container's `db_session` is an async `providers.Resource`, so calling
container providers that depend on it (`rag_agent`, `carousel_agent`,
`conversation_service`) synchronously returns an `_asyncio.Future` instead of
the actual instance. These helpers build the agents directly against a request
scoped `AsyncSession` and pull only the session-free providers (settings,
retriever, external services) from the container.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel_agent import CarouselAgent
from rag_backend.application.services.rag_agent import RAGAgent
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


def build_rag_agent(db: AsyncSession, container: Container) -> RAGAgent:
    """Build a RAGAgent bound to the given per-request session."""
    settings = container.settings()
    carousel_repo = PostgresCarouselRepository(db)
    carousel_agent = CarouselAgent(
        repository=carousel_repo,
        llm_service=container.llm_service(),
        research_tool=container.research_tool(),
        image_service=container.image_service(),
        export_service=container.export_service(),
        output_base_dir=settings.carousel_output_dir,
    )
    return RAGAgent(
        settings=settings,
        retriever=container.retriever(),
        message_repository=PostgresMessageRepository(db),
        document_repository=PostgresDocumentRepository(db),
        carousel_agent=carousel_agent,
        carousel_repository=carousel_repo,
    )
