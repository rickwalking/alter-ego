"""Domain protocols (interfaces) using Python's typing.Protocol.

These protocols define contracts that infrastructure implementations must fulfill.
Using Protocols instead of abstract classes allows for more flexible, decoupled design.
"""

from rag_backend.domain.protocols.ai import Agent, DocumentProcessor, LLMService
from rag_backend.domain.protocols.carousel import (
    CarouselExportService,
    CarouselRefinementService,
    ExportConfig,
    ImageGenerationService,
    ImageStyleStrategy,
    ResearchTool,
    SlideLayoutStrategy,
    StrategyNotFoundError,
)
from rag_backend.domain.protocols.repositories import (
    CarouselRepository,
    ConversationRepository,
    DocumentRepository,
    MessageRepository,
    UserRepository,
)
from rag_backend.domain.protocols.social import PublishResult, SocialPublisher
from rag_backend.domain.protocols.vector import EmbeddingService, Retriever, VectorStore
from rag_backend.domain.protocols.workflow_timeout import StuckWorkflowAutoRejector

__all__ = [
    "Agent",
    "CarouselExportService",
    "CarouselRefinementService",
    "CarouselRepository",
    "ConversationRepository",
    "DocumentProcessor",
    "DocumentRepository",
    "EmbeddingService",
    "ExportConfig",
    "ImageGenerationService",
    "ImageStyleStrategy",
    "LLMService",
    "MessageRepository",
    "PublishResult",
    "ResearchTool",
    "Retriever",
    "SlideLayoutStrategy",
    "SocialPublisher",
    "StrategyNotFoundError",
    "StuckWorkflowAutoRejector",
    "UserRepository",
    "VectorStore",
]
