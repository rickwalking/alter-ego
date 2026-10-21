"""Assertion-bearing tests that pin exact carousel refinement behaviour.

Gherkin:
  tests/features/carousel_image_refinement.feature
  tests/features/carousel_design_refinement.feature
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from structlog.testing import capture_logs

from rag_backend.application.services import carousel_refinement
from rag_backend.domain.models import CarouselProject, CarouselStatus

from .carousel_refinement_helpers import (
    make_refinement_service_with_mocks,
    make_test_slide,
)

MODULE = "rag_backend.application.services.carousel_refinement"
OVERRIDES_FILE = "design_overrides.css"
WRITE_FAILURE_EVENT = "Failed to write design overrides"
SLIDE_EXTRAS: dict[str, object] = {
    "image_prompt": "old scene",
    "features": [{"title": "F"}],
    "stats": [{"value": "42%"}],
    "insight": {"text": "Insight"},
    "translation_en": {"heading": "EN"},
    "summary_points": ["one", "two"],
    "tldr_strip": "TLDR",
}


def _project(tmp_path: Path) -> CarouselProject:
    """A completed project rooted at the temporary directory."""
    return CarouselProject(
        topic="T",
        audience="A",
        niche="N",
        status=CarouselStatus.COMPLETED,
        output_dir=str(tmp_path),
    )


@pytest.fixture
def run_image_one() -> Iterator[AsyncMock]:
    """Patch the single-image generator."""
    with patch(f"{MODULE}.run_image_one", new_callable=AsyncMock) as mock:
        yield mock


def _design_service(
    tmp_path: Path, html: str, css_answer: str
) -> tuple[MagicMock, CarouselProject]:
    """A refinement service wired with a given template HTML and LLM CSS answer."""
    service, repo, _, _ = make_refinement_service_with_mocks()
    agent = cast(MagicMock, service)
    project = _project(tmp_path)
    repo.get_project_by_id = AsyncMock(return_value=project)
    repo.get_slides_by_project = AsyncMock(return_value=[make_test_slide(1)])
    agent._phase4_design = MagicMock(return_value=html)
    agent._llm.generate = AsyncMock(return_value=css_answer)
    return agent, project


def _design_prompt(agent: MagicMock) -> str:
    """The design prompt sent to the LLM."""
    return str(agent._llm.generate.call_args[0][0][0]["content"])


# Scenario: Regenerate image with a new prompt
async def test_regenerate_keeps_structured_cards_and_paths(
    tmp_path: Path, run_image_one: AsyncMock
) -> None:
    """The regenerated slide keeps every structured card and the project paths."""
    service, repo, _, _ = make_refinement_service_with_mocks()
    agent = cast(MagicMock, service)
    project = _project(tmp_path)
    repo.get_project_by_id = AsyncMock(return_value=project)
    slide = make_test_slide(2, extras=dict(SLIDE_EXTRAS))
    repo.get_slides_by_project = AsyncMock(return_value=[slide])
    agent._llm.generate = AsyncMock(return_value="new scene")

    await agent.regenerate_slide_image(project.id, 2, "change it")

    assert run_image_one.await_args is not None
    config = run_image_one.await_args.args[0]
    assert config.project is project
    assert config.output_dir == tmp_path
    assert config.image_registry is agent._image_registry
    assert config.slide.image_prompt == "new scene"
    assert config.slide.stats == SLIDE_EXTRAS["stats"]
    assert config.slide.insight == SLIDE_EXTRAS["insight"]
    assert config.slide.translation_en == SLIDE_EXTRAS["translation_en"]
    assert config.slide.summary_points == SLIDE_EXTRAS["summary_points"]
    assert config.slide.tldr_strip == SLIDE_EXTRAS["tldr_strip"]
    assert config.slide.features == SLIDE_EXTRAS["features"]


# Scenario: A style block right after the first character is still extracted
async def test_design_extracts_style_block_at_index_one(tmp_path: Path) -> None:
    """A style tag at index one is extracted, not treated as missing."""
    agent, project = _design_service(tmp_path, "x<style>.marker-one{}</style>", ".a{}")

    await agent.refine_carousel_design(project.id, "go")

    assert ".marker-one{}" in _design_prompt(agent)


# Scenario: A closing tag without an opening tag yields no CSS
async def test_design_without_opening_tag_sends_no_css(tmp_path: Path) -> None:
    """Only a closing style tag means the CSS excerpt is empty."""
    agent, project = _design_service(tmp_path, "abcdefghij-orphan</style>", ".a{}")

    await agent.refine_carousel_design(project.id, "go")

    assert "orphan" not in _design_prompt(agent)


# Scenario: The CSS excerpt is capped at 2000 characters
async def test_design_css_excerpt_is_capped(tmp_path: Path) -> None:
    """The CSS passed to the design prompt holds at most 2000 characters."""
    css = "a" * 2000 + "b"
    agent, project = _design_service(tmp_path, f"<style>{css}</style>", ".a{}")

    with patch(
        f"{MODULE}._render_design_prompt",
        wraps=carousel_refinement._render_design_prompt,
    ) as render:
        await agent.refine_carousel_design(project.id, "go")

    render.assert_called_once_with("go", "a" * 2000)


# Scenario: Markdown fences are stripped from LLM output
@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("```css.a{}", ".a{}"),
        ("```.b{}", ".b{}"),
        (".c{}```", ".c{}"),
    ],
)
async def test_design_strips_fences_exactly(
    tmp_path: Path, answer: str, expected: str
) -> None:
    """Fence markers are removed without eating CSS characters."""
    agent, project = _design_service(tmp_path, "<style>.x{}</style>", answer)

    await agent.refine_carousel_design(project.id, "go")

    assert (tmp_path / OVERRIDES_FILE).read_text() == expected


# Scenario: A write failure is logged before raising
async def test_design_write_failure_is_logged(tmp_path: Path) -> None:
    """The write failure logs the exact event before raising."""
    agent, project = _design_service(tmp_path, "<style>.x{}</style>", ".a{}")

    with (
        capture_logs() as logs,
        patch.object(Path, "write_text", side_effect=OSError("denied")),
        pytest.raises(ValueError),
    ):
        await agent.refine_carousel_design(project.id, "go")

    assert [log["event"] for log in logs] == [WRITE_FAILURE_EVENT]
