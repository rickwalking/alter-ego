"""Domain protocols (interfaces) using Python's typing.Protocol.

These protocols define contracts that infrastructure implementations must fulfill.
Using Protocols instead of abstract classes allows for more flexible, decoupled design.
"""

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
    Conversation,
    Document,
    DocumentChunk,
    DocumentStatus,
    Message,
    ResearchSource,
    ResearchSourceType,
    RetrievalQuery,
    SearchResult,
)
from rag_backend.domain.types import ChatEvent, PipelineEvent, SparseEmbedding, StatsResponse


class DocumentRepository(Protocol):
    """Protocol for document persistence operations."""

    async def create(self, document: Document) -> Document:
        """Create a new document."""
        ...

    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Get a document by its ID."""
        ...

    async def get_all(
        self, status: DocumentStatus | None = None, limit: int = 100, offset: int = 0
    ) -> list[Document]:
        """Get all documents with optional filtering."""
        ...

    async def update(self, document: Document) -> Document:
        """Update an existing document."""
        ...

    async def delete(self, document_id: UUID) -> bool:
        """Delete a document by ID."""
        ...

    async def count(self, status: DocumentStatus | None = None) -> int:
        """Count documents with optional status filter."""
        ...


class ConversationRepository(Protocol):
    """Protocol for conversation persistence operations."""

    async def create(self, conversation: Conversation) -> Conversation:
        """Create a new conversation."""
        ...

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        """Get a conversation by its ID."""
        ...

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[Conversation]:
        """Get all conversations ordered by updated_at desc."""
        ...

    async def update(self, conversation: Conversation) -> Conversation:
        """Update an existing conversation."""
        ...

    async def delete(self, conversation_id: UUID) -> bool:
        """Delete a conversation and all its messages."""
        ...


class MessageRepository(Protocol):
    """Protocol for message persistence operations."""

    async def create(self, message: Message) -> Message:
        """Create a new message."""
        ...

    async def get_by_conversation(self, conversation_id: UUID, limit: int = 100) -> list[Message]:
        """Get all messages for a conversation."""
        ...

    async def get_recent_context(
        self, conversation_id: UUID, max_tokens: int = 4000
    ) -> list[Message]:
        """Get recent messages that fit within token limit."""
        ...


class VectorStore(Protocol):
    """Protocol for vector database operations."""

    async def upsert_chunks(self, chunks: list[DocumentChunk], document_id: UUID) -> None:
        """Store document chunks with their embeddings."""
        ...

    async def delete_by_document(self, document_id: UUID) -> None:
        """Delete all chunks belonging to a document."""
        ...

    async def hybrid_search(
        self,
        query: str,
        dense_embedding: list[float],
        sparse_embedding: SparseEmbedding,
        top_k: int = 5,
        alpha: float = 0.5,
    ) -> list[SearchResult]:
        """Perform hybrid search combining dense and sparse vectors."""
        ...

    async def get_stats(self) -> StatsResponse:
        """Get vector store statistics."""
        ...


class EmbeddingService(Protocol):
    """Protocol for text embedding generation."""

    async def embed_dense(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embeddings for texts."""
        ...

    async def embed_sparse(self, texts: list[str]) -> list[SparseEmbedding]:
        """Generate sparse (BM25) embeddings for texts."""
        ...

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        ...


class LLMService(Protocol):
    """Protocol for LLM interactions."""

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a complete response."""
        ...

    def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response.

        Implementations are async generators (use `yield`). The method is
        declared with plain `def` rather than `async def` so mypy matches the
        async-generator return type (`AsyncIterator[str]`) rather than
        `Coroutine[..., AsyncIterator[str]]`.
        """
        ...


class DocumentProcessor(Protocol):
    """Protocol for document chunking and processing."""

    async def process(self, document: Document) -> list[DocumentChunk]:
        """Process document into chunks with embeddings."""
        ...

    def estimate_chunks(self, content: str) -> int:
        """Estimate number of chunks for content."""
        ...


class Retriever(Protocol):
    """Protocol for hybrid retrieval with RRF fusion."""

    async def retrieve(self, request: RetrievalQuery) -> list[SearchResult]:
        """Retrieve relevant chunks using hybrid search.

        Takes a single `RetrievalQuery` model bundling the query text,
        top_k, alpha, and optional metadata filters. Keeps the protocol
        surface stable as new retrieval knobs are added.
        """
        ...


class Agent(Protocol):
    """Protocol for the RAG agent."""

    async def chat(
        self, message: str, conversation_id: UUID, *, stream: bool = True
    ) -> AsyncIterator[ChatEvent]:
        """Process a chat message with optional streaming."""
        ...

    async def search_documents(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search for relevant documents."""
        ...


# =============================================================================
# Carousel Content Pipeline Protocols
# =============================================================================


class CarouselRepository(Protocol):
    """Protocol for carousel project persistence operations."""

    async def create_project(self, project: CarouselProject) -> CarouselProject:
        """Create a new carousel project."""
        ...

    async def get_project_by_id(self, project_id: UUID) -> CarouselProject | None:
        """Get a carousel project by its ID."""
        ...

    async def get_all_projects(
        self, status: CarouselStatus | None = None, limit: int = 100, offset: int = 0
    ) -> list[CarouselProject]:
        """Get all carousel projects with optional filtering."""
        ...

    async def update_project(self, project: CarouselProject) -> CarouselProject:
        """Update an existing carousel project."""
        ...

    async def delete_project(self, project_id: UUID) -> bool:
        """Delete a carousel project and its slides."""
        ...

    async def create_slide(self, slide: CarouselSlide) -> CarouselSlide:
        """Create a new carousel slide."""
        ...

    async def get_slides_by_project(self, project_id: UUID) -> list[CarouselSlide]:
        """Get all slides for a project ordered by slide_number."""
        ...

    async def update_slide(self, slide: CarouselSlide) -> CarouselSlide:
        """Update an existing carousel slide."""
        ...

    async def delete_slides_by_project(self, project_id: UUID) -> bool:
        """Delete all slides for a project."""
        ...

    async def create_research_source(self, source: ResearchSource) -> ResearchSource:
        """Create a new research source."""
        ...

    async def get_sources_by_project(self, project_id: UUID) -> list[ResearchSource]:
        """Get all research sources for a project."""
        ...


class ImageGenerationService(Protocol):
    """Protocol for AI image generation.

    Implementations wrap a concrete vendor SDK (Gemini, OpenAI, ...) so
    the agent pipeline can stay provider-agnostic. The caller is
    responsible for composing the final prompt (style wrapper + scene)
    before invoking `generate_image` — this protocol only handles the
    vendor call and persistence to disk.
    """

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
    ) -> str:
        """Generate an image from a text prompt and save to output_path.

        Returns the path to the saved image file.
        """
        ...


class ImageStyleStrategy(Protocol):
    """Protocol for wrapping an LLM-produced scene description with
    provider- and style-specific directives.

    Each (model, style) preset gets its own strategy so the style
    vocabulary can be tuned to what each model responds to best. The
    scene text is treated as user data and MUST appear verbatim in the
    output; the wrapper only prepends directives.
    """

    def wrap(self, scene: str, theme: Mapping[str, str]) -> str:
        """Return the final prompt for the image service.

        Args:
            scene: The LLM-generated scene description, user-owned text.
            theme: Palette dict with at minimum `primary`, `accent`,
                `background` hex strings.
        """
        ...


class CarouselExportService(Protocol):
    """Protocol for carousel HTML to image export."""

    async def export_slides(
        self,
        html_content: str,
        output_dir: str,
        width: int = 1080,
        height: int = 1350,
    ) -> list[str]:
        """Render HTML carousel and export individual slide images.

        Returns list of paths to exported slide images.
        """
        ...


class ResearchTool(Protocol):
    """Protocol for web research operations."""

    async def scrape_url(self, url: str) -> str:
        """Scrape and extract content from a URL."""
        ...

    async def search_web(
        self, query: str, _source_types: list[ResearchSourceType]
    ) -> list[dict[str, str]]:
        """Search the web for relevant sources.

        Returns list of dicts with 'url', 'title', 'snippet' keys.
        """
        ...


class CarouselAgent(Protocol):
    """Protocol for the carousel content generation sub-agent."""

    async def execute_pipeline(
        self,
        project_id: UUID,
        seed_urls: list[str] | None = None,
    ) -> CarouselProject:
        """Execute the full 7-phase carousel generation pipeline.

        Returns the updated project with status COMPLETED or FAILED.
        """
        ...

    async def resume_pipeline(self, project_id: UUID) -> CarouselProject:
        """Resume an interrupted pipeline from its last checkpoint.

        Raises RuntimeError when no checkpointer is configured.
        """
        ...

    def stream_pipeline(
        self,
        project_id: UUID,
        seed_urls: list[str] | None = None,
    ) -> AsyncIterator[PipelineEvent]:
        """Run the pipeline and yield SSE-shaped events.

        Each event is a dict with `node`, `status`, `phase_progress`.
        Terminates with `{"node": "end", ...}` or `{"node": "error", ...}`.
        """
        ...

    def start_pipeline(
        self,
        project_id: UUID,
        seed_urls: list[str] | None = None,
    ) -> None:
        """Start the graph producer in the background if not already running.

        Idempotent: no-op when a task for the project is already alive.
        The frontend should poll `/status` or connect to `/stream` after
        calling this.
        """
        ...

    async def re_render_slides(self, project_id: UUID) -> CarouselProject:
        """Re-render slide JPGs and PDF after text edits.

        Reads slides from the DB, re-renders PT (and EN if available),
        and bumps `updated_at` for cache-busting.
        """
        ...

    async def regenerate_slide_image(
        self,
        project_id: UUID,
        slide_number: int,
        instruction: str,
    ) -> CarouselProject:
        """Regenerate the hero image for a single slide.

        Rewrites the slide's `image_prompt` via LLM using *instruction*,
        generates a new image, and re-exports the slides so the user
        sees the updated artifact immediately.
        """
        ...

    async def refine_carousel_design(
        self,
        project_id: UUID,
        instruction: str,
    ) -> CarouselProject:
        """Apply a CSS/layout design change to the carousel.

        Uses the LLM to translate a natural-language design request into
        CSS overrides, writes them to the project's output directory,
        and re-exports the slide JPGs + PDF so the user sees the new
        layout immediately. Does NOT regenerate source images.
        """
        ...


class SocialPublisher(Protocol):
    """Protocol for publishing a carousel to a social network.

    Implementations translate project content + media into whatever the
    vendor SDK needs. The agent pipeline talks only to this interface,
    so swapping Meta Graph API for a broker (Publer, Ayrshare) later is
    a one-class change.
    """

    async def publish_instagram(
        self,
        caption: str,
        image_urls: list[str],
    ) -> "PublishResult":
        """Publish an Instagram carousel post.

        Args:
            caption: Instagram caption (<= 2200 chars, <= 30 hashtags).
            image_urls: Public HTTPS URLs of each slide, in order.

        Returns a PublishResult with the vendor post ID or an error.
        """
        ...


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a publishing call."""

    status: str  # "queued" | "published" | "failed"
    post_id: str | None = None
    error_message: str | None = None
