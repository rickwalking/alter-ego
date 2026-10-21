"""The images gate expects one hero image per illustrated slide.

Prod 2026-10-14, carousel 8e350d6e: the image phase stored 6 hero images
(``images/slide_1.jpg`` .. ``slide_6.jpg``). Slide 7 is the CTA, rendered with
the owner avatar, so it never gets one. The policy compared the 6 images with
``slides_total`` (7), revised, regenerated the same 6, and escalated: every
real run failed at the images gate.

Gherkin: tests/features/autopilot_runner.feature (hero image count scenarios)
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rag_backend.application.services.carousel.outline_normalize import (
    canonical_slide_type,
)
from rag_backend.domain.constants import SLIDE_TYPE_CTA
from rag_backend.domain.constants.persona import VOICE_MATCH_MIN_SCORE
from rag_backend.modules.autopilot.constants import (
    GATE_IMAGES,
    PHASE_STATUS_AWAITING,
    REASON_IMAGES,
    REASON_PASSED,
)
from rag_backend.modules.autopilot.domain.gate import (
    GateAction,
    GateSnapshot,
    ImageFact,
    SnapshotParts,
)
from rag_backend.modules.autopilot.domain.policy import decide
from rag_backend.modules.autopilot.domain.snapshot import assemble_snapshot
from rag_backend.modules.autopilot.infrastructure import editorial_driver
from rag_backend.modules.editorial.domain.models import CarouselProject, CarouselSlide
from rag_backend.modules.editorial.infrastructure.carousel_automation import (
    CarouselAutomationAcl,
    hero_image_total,
)

_SLIDES = 7
_HERO_IMAGES = 6
_HERO_WIDTH = 1536
_HERO_HEIGHT = 1024
_PROJECT_ID = uuid4()


def _slide(number: int, prompt: str | None = "scene") -> CarouselSlide:
    return CarouselSlide(
        project_id=_PROJECT_ID,
        slide_number=number,
        slide_type=canonical_slide_type(number),
        heading=f"Slide {number}",
        body="body",
        image_prompt=prompt,
    )


def _seven_slides() -> list[CarouselSlide]:
    return [_slide(number) for number in range(1, _SLIDES + 1)]


def _jpeg() -> ImageFact:
    return ImageFact(present=True, is_jpeg=True, width=_HERO_WIDTH, height=_HERO_HEIGHT)


def _gate(images: int, hero_total: int = _HERO_IMAGES) -> GateSnapshot:
    return GateSnapshot(
        phase=GATE_IMAGES,
        phase_status=PHASE_STATUS_AWAITING,
        lock_version=1,
        sources=(),
        outline_count=_SLIDES,
        slides_total=_SLIDES,
        persona_score=VOICE_MATCH_MIN_SCORE,
        forbidden_hits=(),
        presentation_blockers=(),
        images=tuple(_jpeg() for _ in range(images)),
        revisions_used=0,
        stale=False,
        hero_images_total=hero_total,
    )


def _outcome(snapshot: GateSnapshot) -> tuple[GateAction, str]:
    decision = decide(snapshot)
    return decision.action, decision.reason


def test_the_cta_slide_gets_no_hero_image() -> None:
    """Scenario: A 7-slide carousel expects 6 hero images (the CTA uses the avatar)."""
    slides = _seven_slides()
    assert slides[-1].slide_type == SLIDE_TYPE_CTA
    assert hero_image_total(slides) == _HERO_IMAGES


def test_a_slide_without_an_image_prompt_is_not_expected() -> None:
    """The count is the image phase's own filter: no prompt, no hero image."""
    slides = [*_seven_slides()[:-2], _slide(6, prompt=None), _slide(7)]
    assert hero_image_total(slides) == _HERO_IMAGES - 1
    assert hero_image_total([]) == 0


@pytest.mark.asyncio
async def test_the_acl_counts_the_persisted_slides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The editorial facade reads the persisted slides, the image phase's source."""
    acl = CarouselAutomationAcl(AsyncMock())
    project = CarouselProject(topic="t", audience="a", niche="ai", id=_PROJECT_ID)
    slides = AsyncMock(return_value=_seven_slides())
    monkeypatch.setattr(acl, "load_project", AsyncMock(return_value=project))
    monkeypatch.setattr(acl.repository, "get_slides_by_project", slides)
    assert await acl.hero_image_total(str(_PROJECT_ID)) == _HERO_IMAGES
    slides.assert_awaited_once_with(_PROJECT_ID)


@pytest.mark.asyncio
async def test_an_unknown_project_expects_no_hero_images(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing project fails closed at zero (the gate then revises)."""
    acl = CarouselAutomationAcl(AsyncMock())
    monkeypatch.setattr(acl, "load_project", AsyncMock(return_value=None))
    assert await acl.hero_image_total(str(_PROJECT_ID)) == 0


def test_the_snapshot_carries_the_hero_image_count() -> None:
    parts = SnapshotParts(
        state={},
        images=(),
        slides_total=_SLIDES,
        lock_version=1,
        stale=False,
        hero_images_total=_HERO_IMAGES,
    )
    assert assemble_snapshot(parts).hero_images_total == _HERO_IMAGES


def test_six_hero_images_and_a_cta_slide_approve() -> None:
    """Scenario: The images gate approves 6 hero images on a 7-slide carousel."""
    assert _outcome(_gate(_HERO_IMAGES)) == (GateAction.APPROVE, REASON_PASSED)


@pytest.mark.parametrize("count", [_HERO_IMAGES - 1, _SLIDES, 0])
def test_a_wrong_hero_image_count_revises(count: int) -> None:
    """Scenario: A missing or extra hero image is revised."""
    assert _outcome(_gate(count)) == (GateAction.REVISE, REASON_IMAGES)


@pytest.mark.parametrize("hero_total", [0, -1, 11])
def test_an_unknown_hero_image_count_fails_closed(hero_total: int) -> None:
    """No persisted slides (zero) or an out-of-range count never approves."""
    gate = _gate(max(hero_total, 0), hero_total=hero_total)
    assert _outcome(gate) == (GateAction.REVISE, REASON_IMAGES)


def test_a_missing_or_zero_size_file_revises(tmp_path: Path) -> None:
    """Scenario: A missing or zero-size hero image file is revised."""
    empty = tmp_path / "slide_6.jpg"
    empty.write_bytes(b"")
    absent = tmp_path / "slide_5.jpg"
    measured = editorial_driver._images([str(empty), str(absent)])
    assert measured == (
        ImageFact(present=True, is_jpeg=False, width=0, height=0),
        ImageFact(present=False, is_jpeg=False, width=0, height=0),
    )
    good = _gate(_HERO_IMAGES)
    for broken in measured:
        snapshot = replace(good, images=(*good.images[:-1], broken))
        assert _outcome(snapshot) == (GateAction.REVISE, REASON_IMAGES)
