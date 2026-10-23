"""A carousel created from the chat gets the default carousel rubric.

Feature: backend/tests/features/carousel_rubric_ae0504.feature
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

from rag_backend.application.tools.carousel.access import CarouselToolAccessContext
from rag_backend.application.tools.carousel.generate_carousel import (
    build_generate_carousel_tool,
)
from rag_backend.domain.models import CarouselProject

_REQUEST = {"topic": "Topic", "audience": "Audience", "niche": "Niche"}


def _repo() -> AsyncMock:
    repo = AsyncMock()
    repo.create_project = AsyncMock(
        side_effect=lambda project: project,
    )
    return repo


async def test_a_chat_carousel_gets_the_default_rubric() -> None:
    """Scenario: Autopilot and chat carousels get the default carousel rubric."""
    repo = _repo()
    lookup = AsyncMock(return_value="rubric-default")
    access = CarouselToolAccessContext(
        owner_user_id=str(uuid4()), default_rubric_id=lookup
    )

    await build_generate_carousel_tool(repo, access).ainvoke(_REQUEST)

    created: CarouselProject = repo.create_project.call_args.args[0]
    assert created.rubric_id == "rubric-default"
    lookup.assert_awaited_once()


async def test_without_a_lookup_the_chat_carousel_has_no_rubric() -> None:
    """Scenario: Autopilot and chat carousels get the default carousel rubric."""
    repo = _repo()
    access = CarouselToolAccessContext(owner_user_id=str(uuid4()))

    await build_generate_carousel_tool(repo, access).ainvoke(_REQUEST)

    created: CarouselProject = repo.create_project.call_args.args[0]
    assert created.rubric_id is None
