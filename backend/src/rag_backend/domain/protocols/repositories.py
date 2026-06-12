from typing import Protocol, TypedDict
from uuid import UUID

from rag_backend.domain.models import (
    CarouselImageGeneration,
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
    Conversation,
    Document,
    DocumentStatus,
    Message,
    ResearchSource,
    User,
    UserRole,
)


class UserRepository(Protocol):
    """Protocol for user persistence operations."""

    async def create(self, user: User) -> User: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[User]: ...

    async def update(self, user: User) -> User: ...

    async def delete(self, user_id: UUID) -> bool: ...

    async def count(self) -> int: ...

    async def count_by_role(self, role: UserRole) -> int: ...


class DocumentRepository(Protocol):
    """Protocol for document persistence operations."""

    async def create(self, document: Document) -> Document: ...

    async def get_by_id(self, document_id: UUID) -> Document | None: ...

    async def get_all(
        self, status: DocumentStatus | None = None, limit: int = 100, offset: int = 0
    ) -> list[Document]: ...

    async def update(self, document: Document) -> Document: ...

    async def delete(self, document_id: UUID) -> bool: ...

    async def count(self, status: DocumentStatus | None = None) -> int: ...


class _UserQuery(TypedDict, total=False):
    """Bundled query parameters for user conversation listing."""

    user_id: UUID
    limit: int
    offset: int
    origin: str | None


class ConversationRepository(Protocol):
    """Protocol for conversation persistence operations."""

    async def create(self, conversation: Conversation) -> Conversation: ...

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None: ...

    async def get_all(
        self, limit: int = 100, offset: int = 0
    ) -> list[Conversation]: ...

    async def get_by_user_id(
        self,
        query: _UserQuery,
    ) -> list[Conversation]:
        """Return conversations owned by the given user."""
        ...

    async def count_by_user_id(self, user_id: UUID) -> int:
        """Return the number of conversations owned by the given user."""
        ...

    async def update(self, conversation: Conversation) -> Conversation: ...

    async def delete(self, conversation_id: UUID) -> bool: ...


class MessageRepository(Protocol):
    """Protocol for message persistence operations."""

    async def create(self, message: Message) -> Message: ...

    async def get_by_conversation(
        self, conversation_id: UUID, limit: int = 100
    ) -> list[Message]: ...

    async def get_recent_context(
        self, conversation_id: UUID, max_tokens: int = 4000
    ) -> list[Message]: ...


class _ProjectQuery(TypedDict, total=False):
    """Bundled query parameters for carousel project listing."""

    status: CarouselStatus | None
    limit: int
    offset: int
    public_only: bool
    owner_id: str | None


class CarouselRepository(Protocol):
    """Protocol for carousel project persistence operations."""

    async def create_project(self, project: CarouselProject) -> CarouselProject: ...

    async def get_project_by_id(self, project_id: UUID) -> CarouselProject | None: ...

    async def get_all_projects(
        self,
        *,
        query: _ProjectQuery,
    ) -> list[CarouselProject]: ...

    async def update_project(self, project: CarouselProject) -> CarouselProject: ...

    async def delete_project(self, project_id: UUID) -> bool: ...

    async def create_slide(self, slide: CarouselSlide) -> CarouselSlide: ...

    async def get_slides_by_project(self, project_id: UUID) -> list[CarouselSlide]: ...

    async def update_slide(self, slide: CarouselSlide) -> CarouselSlide: ...

    async def get_image_generation_by_key(
        self, generation_key: str
    ) -> CarouselImageGeneration | None: ...

    async def upsert_image_generation(
        self, generation: CarouselImageGeneration
    ) -> CarouselImageGeneration: ...

    async def delete_slides_by_project(self, project_id: UUID) -> bool: ...

    async def create_research_source(
        self, source: ResearchSource
    ) -> ResearchSource: ...

    async def get_sources_by_project(
        self, project_id: UUID
    ) -> list[ResearchSource]: ...
