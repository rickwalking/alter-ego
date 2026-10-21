"""Bulk cover + section images on the editor's image service.

Feature: backend/tests/features/blog_generate_ae0425.feature
"""

from __future__ import annotations

import asyncio
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rag_backend.application.services.blog import blog_image_batch
from rag_backend.application.services.blog.blog_image_batch import (
    ImageBatchRequest,
)
from rag_backend.domain.constants.blog_editor import (
    ERR_BLOG_IMAGE_GENERATION_FAILED,
    ERR_BLOG_IMAGE_PERSIST_FAILED,
)
from rag_backend.domain.constants.blog_generation import (
    ERR_IMAGE_COST_CAP,
    IMAGE_SLOT_COVER,
)
from rag_backend.domain.models.blog_generation import GenerationTrace, ImageSubject
from tests.blog_generation_fakes import (
    FAIL_IMAGE_MARKER,
    FakeImageGenerator,
    image_batch,
)

POST_ID = "11111111-1111-4111-8111-111111111111"
TRACE = GenerationTrace(project_id="proj", user_id="user", post_id=POST_ID)


@pytest.fixture(autouse=True)
def _no_langfuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """The editor's single-image service traces with its own helper."""
    monkeypatch.setattr(
        blog_image_batch,
        "blog_phase_trace",
        lambda _s, **_kwargs: nullcontext(MagicMock()),
    )
    from rag_backend.application.services.blog import blog_image_service as _single

    monkeypatch.setattr(
        _single, "blog_ai_propagate", lambda *_a: nullcontext(MagicMock())
    )


def _subjects(count: int, fail: str | None = None) -> tuple[ImageSubject, ...]:
    cover = ImageSubject(slot=IMAGE_SLOT_COVER, heading="Título", body="Lede")
    sections = tuple(
        ImageSubject(
            slot=f"sec_{index}",
            heading=FAIL_IMAGE_MARKER if f"sec_{index}" == fail else f"Seção {index}",
            body="Corpo",
        )
        for index in range(1, count + 1)
    )
    return (cover, *sections)


def _request(
    count: int, budget: int = 30, fail: str | None = None
) -> ImageBatchRequest:
    return ImageBatchRequest(TRACE, _subjects(count, fail), max_images=budget)


async def test_cover_and_one_image_per_section_are_persisted(tmp_path: Path) -> None:
    """The editor's store yields only canonical same-origin URLs."""
    # Scenario: A cover and one image slot per section are created
    generator = FakeImageGenerator()
    result = await image_batch(tmp_path, generator).generate(_request(4))
    assert set(result.images) == {IMAGE_SLOT_COVER, "sec_1", "sec_2", "sec_3", "sec_4"}
    assert result.errors == ()
    for image in result.images.values():
        assert image.url.startswith(f"/api/blog-images/{POST_ID}/")
        assert (tmp_path / POST_ID / image.url.rsplit("/", 1)[1]).is_file()
        assert image.alt.strip()
        assert image.model == "gpt-image-2"
    assert all("No text, no words, no letters" in p for p in generator.prompts)
    assert "Título" in generator.prompts[0]


async def test_a_failed_image_leaves_the_slot_empty(tmp_path: Path) -> None:
    # Scenario: A failed image leaves the slot empty and does not fail the draft
    result = await image_batch(tmp_path, FakeImageGenerator()).generate(
        _request(4, fail="sec_3")
    )
    assert "sec_3" not in result.images
    assert len(result.images) == 4
    assert result.errors == (
        {
            "slot": "sec_3",
            "code": ERR_BLOG_IMAGE_GENERATION_FAILED,
            "reason": ERR_BLOG_IMAGE_GENERATION_FAILED,
        },
    )


async def test_an_image_that_was_not_written_is_a_failure(tmp_path: Path) -> None:
    result = await image_batch(tmp_path, FakeImageGenerator(write_file=False)).generate(
        _request(1)
    )
    assert result.images == {}
    assert {error["code"] for error in result.errors} == {ERR_BLOG_IMAGE_PERSIST_FAILED}


async def test_the_budget_limits_the_attempted_slots(tmp_path: Path) -> None:
    # Scenario: The per-post image cost cap is enforced
    generator = FakeImageGenerator()
    result = await image_batch(tmp_path, generator).generate(_request(4, budget=3))
    assert len(generator.prompts) == 3
    assert set(result.images) == {IMAGE_SLOT_COVER, "sec_1", "sec_2"}
    capped = [e for e in result.errors if e["code"] == ERR_IMAGE_COST_CAP]
    assert [e["slot"] for e in capped] == ["sec_3", "sec_4"]


async def test_an_exhausted_budget_spends_nothing(tmp_path: Path) -> None:
    generator = FakeImageGenerator()
    result = await image_batch(tmp_path, generator).generate(_request(2, budget=-1))
    assert generator.prompts == []
    assert len(result.errors) == 3


async def test_concurrency_is_bounded(tmp_path: Path) -> None:
    in_flight = 0
    peak = 0

    class SlowGenerator(FakeImageGenerator):
        async def generate_image(self, prompt: str, output_path: str) -> str:
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.01)
            in_flight -= 1
            return await super().generate_image(prompt, output_path)

    await image_batch(tmp_path, SlowGenerator()).generate(_request(5))
    assert peak == 2


async def test_discard_deletes_the_new_files(tmp_path: Path) -> None:
    batch = image_batch(tmp_path, FakeImageGenerator())
    result = await batch.generate(_request(1))
    assert len(list((tmp_path / POST_ID).iterdir())) == 2
    batch.discard(POST_ID, result.images)
    assert list((tmp_path / POST_ID).iterdir()) == []
