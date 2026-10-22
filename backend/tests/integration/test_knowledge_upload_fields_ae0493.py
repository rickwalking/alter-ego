"""The upload route reads title, tags, scope and is_public from the multipart body.

Gherkin: tests/features/knowledge_upload_fields_ae0493.feature
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from rag_backend.api.dependencies.knowledge import get_knowledge_service
from rag_backend.api.schemas.documents import DocumentUploadResponse
from rag_backend.domain.models import DocumentScope
from rag_backend.modules.knowledge.domain.commands import IngestDocumentCommand
from tests.integration.test_knowledge_safety_net import (
    KnowledgeEnv,
    kb_env,
)

__all__ = ["kb_env"]

FILE_NAME = "notes.txt"
FILE_FIELD = {"file": (FILE_NAME, b"Some notes", "text/plain")}


def _uploaded(command: IngestDocumentCommand) -> DocumentUploadResponse:
    now = datetime.now(UTC)
    return DocumentUploadResponse(
        id=uuid4(),
        title=command.title,
        status="completed",
        metadata=dict(command.metadata),
        chunk_count=1,
        scope=command.scope.value,
        is_public=command.is_public,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def ingest(kb_env: KnowledgeEnv) -> Iterator[AsyncMock]:
    service = AsyncMock()
    service.ingest = AsyncMock(side_effect=_uploaded)
    kb_env.app.dependency_overrides[get_knowledge_service] = lambda: service
    yield service.ingest
    kb_env.app.dependency_overrides.pop(get_knowledge_service, None)


def _command(ingest: AsyncMock) -> IngestDocumentCommand:
    command = ingest.await_args.args[0]
    assert isinstance(command, IngestDocumentCommand)
    return command


@pytest.mark.integration
class TestKnowledgeUploadFields:
    async def test_typed_title_and_tags_are_saved(
        self, kb_env: KnowledgeEnv, ingest: AsyncMock
    ) -> None:
        # Scenario: The typed title and tags are saved
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.post(
                "/api/documents/upload",
                files=FILE_FIELD,
                data={"title": "Meu currículo", "tags": "cv, carreira , "},
            )

        assert response.status_code == 201
        assert response.json()["title"] == "Meu currículo"
        command = _command(ingest)
        assert command.title == "Meu currículo"
        assert command.metadata["tags"] == "cv,carreira"
        assert command.metadata["filename"] == FILE_NAME

    async def test_file_name_is_the_title_without_one(
        self, kb_env: KnowledgeEnv, ingest: AsyncMock
    ) -> None:
        # Scenario: Without a title the file name is used
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.post("/api/documents/upload", files=FILE_FIELD)

        assert response.status_code == 201
        command = _command(ingest)
        assert command.title == FILE_NAME
        assert "tags" not in command.metadata
        assert command.scope is DocumentScope.PERSONAL
        assert command.is_public is False

    async def test_scope_and_public_flag_come_from_the_form(
        self, kb_env: KnowledgeEnv, ingest: AsyncMock
    ) -> None:
        # Scenario: The scope and public flag come from the same form
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.post(
                "/api/documents/upload",
                files=FILE_FIELD,
                data={"scope": "public", "is_public": "true"},
            )

        assert response.status_code == 201
        command = _command(ingest)
        assert command.scope is DocumentScope.PUBLIC
        assert command.is_public is True

    async def test_unknown_scope_is_rejected(
        self, kb_env: KnowledgeEnv, ingest: AsyncMock
    ) -> None:
        # Scenario: An unknown scope is still rejected
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.post(
                "/api/documents/upload",
                files=FILE_FIELD,
                data={"scope": "everyone"},
            )

        assert response.status_code == 400
        assert ingest.await_count == 0
