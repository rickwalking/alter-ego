"""PostgreSQL repository implementations using SQLAlchemy."""

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models import Document, DocumentStatus
from rag_backend.infrastructure.database.models import DocumentModel

_ERR_DOCUMENT_NOT_FOUND = "Document with id {} not found"


class PostgresDocumentRepository:
    """PostgreSQL implementation of DocumentRepository protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: Document) -> Document:
        """Create a new document."""
        db_document = DocumentModel.from_entity(document)
        self._session.add(db_document)
        await self._session.flush()
        return db_document.to_entity()

    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Get a document by its ID."""
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.id == str(document_id))
        )
        db_document = result.scalar_one_or_none()
        return db_document.to_entity() if db_document else None

    async def get_all(
        self, status: DocumentStatus | None = None, limit: int = 100, offset: int = 0
    ) -> list[Document]:
        """Get all documents with optional filtering."""
        query = select(DocumentModel)

        if status:
            query = query.where(DocumentModel.status == status.value)

        query = query.order_by(desc(DocumentModel.updated_at)).offset(offset).limit(limit)
        result = await self._session.execute(query)
        return [doc.to_entity() for doc in result.scalars().all()]

    async def update(self, document: Document) -> Document:
        """Update an existing document."""
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.id == str(document.id))
        )
        db_document = result.scalar_one_or_none()
        if not db_document:
            raise ValueError(_ERR_DOCUMENT_NOT_FOUND.format(document.id))

        db_document.update_from_entity(document)
        await self._session.flush()
        return db_document.to_entity()

    async def delete(self, document_id: UUID) -> bool:
        """Delete a document by ID."""
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.id == str(document_id))
        )
        db_document = result.scalar_one_or_none()
        if not db_document:
            return False

        await self._session.delete(db_document)
        await self._session.flush()
        return True

    async def count(self, status: DocumentStatus | None = None) -> int:
        """Count documents with optional status filter."""
        query = select(func.count()).select_from(DocumentModel)
        if status:
            query = query.where(DocumentModel.status == status.value)

        result = await self._session.execute(query)
        return result.scalar() or 0
