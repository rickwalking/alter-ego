"""Unit tests for _resolve_refine_target.

Gherkin: tests/features/carousel_refine.feature
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from rag_backend.application.tools.carousel.refine_copy import _resolve_refine_target
from rag_backend.domain.models import CarouselProject, CarouselSlide


def _project() -> CarouselProject:
    return CarouselProject(
        topic="T",
        audience="A",
        niche="N",
        caption="original caption #one",
        linkedin_post_pt="post em português",
        linkedin_post_en="English post",
    )


def _slide(number: int, heading: str = "Heading", body: str = "Body") -> CarouselSlide:
    import uuid

    return CarouselSlide(
        project_id=uuid.uuid4(),
        slide_number=number,
        slide_type="content",
        heading=heading,
        body=body,
    )


def _repo_with_slides(slides: list[CarouselSlide] | None = None) -> AsyncMock:
    repo = AsyncMock()
    repo.update_project = AsyncMock()
    repo.update_slide = AsyncMock()
    repo.get_slides_by_project = AsyncMock(return_value=slides or [])
    return repo


@pytest.mark.unit
class TestResolveRefineTarget:
    """Target resolution + persistence for every supported selector."""

    async def test_instagram_caption(self) -> None:
        proj = _project()
        repo = _repo_with_slides()
        original, setter = await _resolve_refine_target(proj, "instagram_caption", repo)
        assert original == "original caption #one"
        await setter("new caption")
        assert proj.caption == "new caption"
        repo.update_project.assert_awaited_once()

    async def test_linkedin_post_pt(self) -> None:
        proj = _project()
        repo = _repo_with_slides()
        original, setter = await _resolve_refine_target(proj, "linkedin_post_pt", repo)
        assert original == "post em português"
        await setter("novo post")
        assert proj.linkedin_post_pt == "novo post"
        repo.update_project.assert_awaited_once()

    async def test_linkedin_post_en(self) -> None:
        proj = _project()
        repo = _repo_with_slides()
        original, setter = await _resolve_refine_target(proj, "linkedin_post_en", repo)
        assert original == "English post"
        await setter("new English")
        assert proj.linkedin_post_en == "new English"

    async def test_slide_heading_updates_target_slide(self) -> None:
        proj = _project()
        slides = [_slide(1), _slide(2, heading="Second")]
        repo = _repo_with_slides(slides)
        original, setter = await _resolve_refine_target(proj, "slide_heading:2", repo)
        assert original == "Second"
        await setter("Rewritten")
        assert slides[1].heading == "Rewritten"
        repo.update_slide.assert_awaited_once()

    async def test_slide_body_updates_target_slide(self) -> None:
        proj = _project()
        slides = [_slide(1, body="First body"), _slide(2, body="Second body")]
        repo = _repo_with_slides(slides)
        original, setter = await _resolve_refine_target(proj, "slide_body:1", repo)
        assert original == "First body"
        await setter("Bullet 1\nBullet 2")
        assert slides[0].body == "Bullet 1\nBullet 2"

    async def test_unknown_target_returns_none(self) -> None:
        proj = _project()
        repo = _repo_with_slides()
        original, setter = await _resolve_refine_target(proj, "blog_footer", repo)
        assert original is None
        await setter("whatever")  # no-op, should not raise
        repo.update_project.assert_not_awaited()
        repo.update_slide.assert_not_awaited()

    async def test_invalid_slide_number_returns_none(self) -> None:
        proj = _project()
        repo = _repo_with_slides()
        original, _ = await _resolve_refine_target(proj, "slide_heading:not-a-number", repo)
        assert original is None

    async def test_out_of_range_slide_returns_none(self) -> None:
        proj = _project()
        slides = [_slide(1), _slide(2)]
        repo = _repo_with_slides(slides)
        original, _ = await _resolve_refine_target(proj, "slide_heading:99", repo)
        assert original is None
