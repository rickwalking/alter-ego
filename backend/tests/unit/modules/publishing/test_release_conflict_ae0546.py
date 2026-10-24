"""The public release retries a lost version race and fails cleanly when it keeps losing.

Feature: backend/tests/features/approve_keeps_caption_ae0546.feature
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.domain.models import CarouselProject
from rag_backend.modules.autopilot.domain.owner_ports import ReleaseCommand
from rag_backend.modules.autopilot.infrastructure import carousel_release
from rag_backend.modules.autopilot.infrastructure.carousel_release import (
    PublishingCarouselReleaser,
)
from rag_backend.modules.publishing import CarouselRepository, LegacyPublishingAcl


def _session(*rowcounts: int) -> AsyncMock:
    session = AsyncMock()
    session.scalar.return_value = 2
    session.execute.side_effect = [MagicMock(rowcount=count) for count in rowcounts]
    return session


async def test_a_release_that_loses_one_race_retries_and_commits() -> None:
    """Scenario: The public release never overwrites a caption edited after the load"""
    project = CarouselProject(topic="AI", audience="devs", niche="tech")
    session = _session(0, 1)
    acl = LegacyPublishingAcl(session, AsyncMock(spec=CarouselRepository))

    released = await acl.release_public(project, str(project.id))

    assert released is project
    assert project.is_public is True
    assert session.execute.await_count == 2
    session.commit.assert_awaited_once()


class _Automation:
    def __init__(self, _session: object) -> None:
        self.repository = AsyncMock(spec=CarouselRepository)

    async def load_project(self, _project_id: str) -> CarouselProject:
        return CarouselProject(topic="AI", audience="devs", niche="tech")


@pytest.mark.parametrize(("rowcounts", "released"), [((0, 0, 0), False), ((1,), True)])
async def test_the_autopilot_release_reports_a_lost_race_as_not_released(
    monkeypatch: pytest.MonkeyPatch, rowcounts: tuple[int, ...], released: bool
) -> None:
    """Scenario: The public release never overwrites a caption edited after the load"""
    monkeypatch.setattr(carousel_release, "CarouselAutomationAcl", _Automation)
    session = _session(*rowcounts)

    result = await PublishingCarouselReleaser(session).release(
        ReleaseCommand(project_id="5350e0ca-ad31-40a1-9e50-70852f1ee484")
    )

    assert result is released
    assert session.commit.await_count == int(released)
