"""Recovery after a scope change or a reprocess that rolled back.

Both runs delete the document's chunks before re-indexing it. When the run
fails afterwards (the commit included), the Unit of Work rolls the row back to
its earlier state, which still claims the old chunks although they are gone.
The recovery deletes whatever a scope change wrote to the new namespace, then
saves the document as failed in a fresh transaction so the Knowledge Base shows
Retry. A failing recovery step is logged and never replaces the run's error.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

import structlog

from rag_backend.domain.constants.documents import FAILURE_PROCESSING_ERROR
from rag_backend.modules.knowledge.domain.models import DocumentScope
from rag_backend.modules.knowledge.domain.ports import DocumentRepository
from rag_backend.platform.database import UnitOfWork

logger = structlog.get_logger()

_LOG_DROP_FAILED = "knowledge_rescope_drop_chunks_failed"
_LOG_MARK_FAILED = "knowledge_reindex_mark_failed_failed"
_LOG_MARKED_FAILED = "knowledge_reindex_rolled_back"


class ChunkDropper(Protocol):
    """The pipeline operation that deletes a document's chunks from a scope."""

    async def drop_chunks(self, document_id: str, scope: DocumentScope) -> None: ...


class ReindexRecovery:
    """Cleans up after a rolled-back scope change or reprocess."""

    def __init__(
        self,
        repository: DocumentRepository,
        pipeline: ChunkDropper,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._repository = repository
        self._pipeline = pipeline
        self._unit_of_work = unit_of_work

    async def after_failed_rescope(
        self, document_id: UUID, scope: DocumentScope
    ) -> None:
        """Drop the chunks written to ``scope``, then mark the document failed."""
        try:
            await self._pipeline.drop_chunks(str(document_id), scope)
        except Exception:
            logger.exception(
                _LOG_DROP_FAILED, document_id=str(document_id), scope=scope.value
            )
        await self.after_failed_reprocess(document_id)

    async def after_failed_reprocess(self, document_id: UUID) -> None:
        """Save the document as failed in a fresh transaction, if it still exists."""
        try:
            await self._unit_of_work.rollback()
            async with self._unit_of_work:
                document = await self._repository.get_by_id(document_id)
                if document is None:
                    return
                document.mark_failed(FAILURE_PROCESSING_ERROR)
                document.chunk_count = 0
                await self._repository.update(document)
        except Exception:
            logger.exception(_LOG_MARK_FAILED, document_id=str(document_id))
            return
        logger.warning(_LOG_MARKED_FAILED, document_id=str(document_id))
