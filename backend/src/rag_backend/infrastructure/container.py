"""Dependency injection container.

Provides centralized dependency management following Clean Architecture principles.
All dependencies are configured here and injected into the application layer.
"""

from dependency_injector import containers, providers

from rag_backend.application.services.carousel_agent import CarouselAgent
from rag_backend.application.services.conversation_service import ConversationService
from rag_backend.application.services.document_pipeline import (
    DocumentProcessingPipeline,
)
from rag_backend.application.services.rag_agent import RAGAgent
from rag_backend.application.services.tools.export_tool import CarouselExportTool
from rag_backend.application.services.tools.image_tool import ImageGenerationTool
from rag_backend.application.services.tools.research_tool import PlaywrightResearchTool
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.database.conversation_repository import (
    PostgresConversationRepository,
    PostgresMessageRepository,
)
from rag_backend.infrastructure.database.document_repository import (
    PostgresDocumentRepository,
)
from rag_backend.infrastructure.external.anthropic_llm import AnthropicLLMService
from rag_backend.infrastructure.external.gemini_image import GeminiImageService
from rag_backend.infrastructure.external.openai_embeddings import (
    OpenAIEmbeddingService,
)
from rag_backend.infrastructure.external.pinecone_store import PineconeVectorStore
from rag_backend.infrastructure.external.playwright_export import PlaywrightExportService
from rag_backend.infrastructure.retrieval.document_processor import (
    RecursiveDocumentProcessor,
)
from rag_backend.infrastructure.retrieval.hybrid_retriever import HybridRetrieverWithRRF


class Container(containers.DeclarativeContainer):
    """Dependency injection container for the RAG backend."""

    # Configuration
    settings = providers.Singleton(get_settings)

    # Database session - provided at runtime per-request
    db_session = providers.Resource(get_session)

    # Repositories
    document_repository = providers.Factory(
        PostgresDocumentRepository,
        session=db_session,
    )

    conversation_repository = providers.Factory(
        PostgresConversationRepository,
        session=db_session,
    )

    message_repository = providers.Factory(
        PostgresMessageRepository,
        session=db_session,
    )

    # External Services (Singletons - shared state)
    embedding_service = providers.Singleton(
        OpenAIEmbeddingService,
        settings=settings,
    )

    llm_service = providers.Singleton(
        AnthropicLLMService,
        settings=settings,
    )

    vector_store = providers.Singleton(
        PineconeVectorStore,
        settings=settings,
    )

    # Infrastructure Layer
    document_processor = providers.Singleton(
        RecursiveDocumentProcessor,
        embedding_service=embedding_service,
        chunk_size=1000,
        chunk_overlap=200,
    )

    retriever = providers.Singleton(
        HybridRetrieverWithRRF,
        vector_store=vector_store,
        embedding_service=embedding_service,
        default_alpha=0.5,
    )

    # Application Layer Services
    document_pipeline = providers.Factory(
        DocumentProcessingPipeline,
        document_repository=document_repository,
        document_processor=document_processor,
        vector_store=vector_store,
    )

    conversation_service = providers.Factory(
        ConversationService,
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        max_context_tokens=4000,
    )

    # Carousel Pipeline
    carousel_repository = providers.Factory(
        PostgresCarouselRepository,
        session=db_session,
    )

    research_tool = providers.Singleton(PlaywrightResearchTool)

    image_service = providers.Singleton(
        GeminiImageService,
        api_key=settings.provided().gemini_api_key,
    )

    export_service = providers.Singleton(PlaywrightExportService)

    # Application Tools (wrappers around infrastructure services)
    image_generation_tool = providers.Singleton(
        ImageGenerationTool,
        image_service=image_service,
    )

    carousel_export_tool = providers.Singleton(
        CarouselExportTool,
        export_service=export_service,
    )

    carousel_agent = providers.Factory(
        CarouselAgent,
        repository=carousel_repository,
        llm_service=llm_service,
        research_tool=research_tool,
        image_service=image_service,
        export_service=export_service,
        output_base_dir=settings.provided().carousel_output_dir,
    )

    # Agent (after carousel_agent is defined)
    rag_agent = providers.Factory(
        RAGAgent,
        settings=settings,
        retriever=retriever,
        message_repository=message_repository,
        document_repository=document_repository,
        carousel_agent=carousel_agent,
        carousel_repository=carousel_repository,
    )


# Global container instance
container = Container()


def get_container() -> Container:
    """Get the global container instance."""
    return container
