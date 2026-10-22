"""A pipeline failure is logged once and marked for the callers.

Gherkin: tests/features/knowledge_error_detail_ae0452.feature
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.application.services.document_pipeline import (
    PIPELINE_FAILURE_LOGGED,
    DocumentProcessingPipeline,
)
from rag_backend.domain.models import Document, DocumentStatus


async def test_failure_is_marked_as_logged_and_reraised() -> None:
    # Scenario: A pipeline failure is logged with its traceback once
    repository = MagicMock()
    repository.update = AsyncMock()
    processor = MagicMock()
    processor.process = AsyncMock(side_effect=RuntimeError("embedding down"))
    pipeline = DocumentProcessingPipeline(repository, processor, MagicMock())
    document = Document(title="Notes", content="Some notes")

    with pytest.raises(RuntimeError) as caught:
        await pipeline.process_document(document)

    assert PIPELINE_FAILURE_LOGGED in getattr(caught.value, "__notes__", [])
    assert document.status == DocumentStatus.FAILED
