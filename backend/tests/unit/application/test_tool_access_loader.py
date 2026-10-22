"""Shared project loading for the carousel RAG agent tools.

Scenario: an unparsable id returns the invalid-id error.
Scenario: an unknown project returns the not-found error.
Scenario: a project owned by someone else returns the access-denied error.
Scenario: the owner gets the parsed id and project back.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from rag_backend.application.tools.carousel.access import (
    CarouselToolAccessContext,
    load_authorized_project,
)
from rag_backend.domain.constants.access_control import ERR_CAROUSEL_TOOL_ACCESS_DENIED
from rag_backend.domain.constants.carousel_tools import (
    ERR_CAROUSEL_TOOL_INVALID_PROJECT_ID,
    ERR_CAROUSEL_TOOL_PROJECT_NOT_FOUND,
)

_ACCESS = CarouselToolAccessContext(owner_user_id="owner-1")


def _repository(project: object | None) -> MagicMock:
    repository = MagicMock()
    repository.get_project_by_id = AsyncMock(return_value=project)
    return repository


# Scenario: an unparsable id returns the invalid-id error.
async def test_invalid_uuid_returns_invalid_id_error() -> None:
    repository = _repository(None)

    result = await load_authorized_project("nope", repository, _ACCESS)

    assert result == ERR_CAROUSEL_TOOL_INVALID_PROJECT_ID
    repository.get_project_by_id.assert_not_awaited()


# Scenario: an unknown project returns the not-found error.
async def test_missing_project_returns_not_found_error() -> None:
    result = await load_authorized_project(str(uuid4()), _repository(None), _ACCESS)

    assert result == ERR_CAROUSEL_TOOL_PROJECT_NOT_FOUND


# Scenario: a project owned by someone else returns the access-denied error.
async def test_foreign_project_returns_access_denied() -> None:
    project = MagicMock(owner_id="someone-else")

    result = await load_authorized_project(str(uuid4()), _repository(project), _ACCESS)

    assert result == ERR_CAROUSEL_TOOL_ACCESS_DENIED


# Scenario: the owner gets the parsed id and project back.
async def test_owner_gets_uuid_and_project() -> None:
    project = MagicMock(owner_id="owner-1")
    project_id = uuid4()

    result = await load_authorized_project(
        str(project_id), _repository(project), _ACCESS
    )

    assert result == (project_id, project)
