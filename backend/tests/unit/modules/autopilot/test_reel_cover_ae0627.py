"""Reel covers: 9:16 validation, the purpose field, and the topic-side guard.

Gherkin: tests/features/reel_cover_asset_ae0627.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from PIL import Image

from rag_backend.application.services.carousel.cover_asset_validation import (
    CoverImageUpload,
    is_reel_ratio,
    validate_cover_image,
)
from rag_backend.domain.models.slide_cover import CoverAssetError
from rag_backend.modules.autopilot.application.cover_upload import (
    CoverUploadCommand,
    CoverUploadDependencies,
    CoverUploadService,
)
from rag_backend.modules.autopilot.domain.cover import (
    CoverAsset,
    CoverCheck,
    CoverFacts,
    CoverForm,
    cover_reason,
    form_problem,
    form_purpose,
)
from rag_backend.modules.autopilot.domain.cover_ports import CoverImage, StoredImage
from tests.unit.modules.autopilot.repost_fakes import NOW, Clock, reel_cover


def _png(size: tuple[int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


# Scenario: A 9:16 reel cover is accepted at 1080x1920
# Scenario: A larger 9:16 reel cover is scaled, never cropped
@pytest.mark.parametrize("size", [(1080, 1920), (1440, 2560), (1088, 1920)])
def test_reel_cover_is_scaled_to_1080x1920(size: tuple[int, int]) -> None:
    out = validate_cover_image(
        CoverImageUpload(content=_png(size), kind="ai_image", purpose="reel_cover")
    )
    assert (out.width, out.height) == (1080, 1920)


# Scenario: A reel cover that is not 9:16 is refused
# Scenario: A reel cover smaller than 1080x1920 is refused
@pytest.mark.parametrize(
    ("size", "code"),
    [
        ((1080, 1350), "asset_ratio_invalid"),
        ((1920, 1080), "asset_ratio_invalid"),
        ((720, 1280), "asset_too_small"),
    ],
)
def test_reel_cover_refusals(size: tuple[int, int], code: str) -> None:
    with pytest.raises(CoverAssetError) as error:
        validate_cover_image(
            CoverImageUpload(content=_png(size), kind="ai_image", purpose="reel_cover")
        )
    assert error.value.code == code


# Scenario: An upload without purpose stays a carousel cover
def test_carousel_cover_unchanged() -> None:
    out = validate_cover_image(
        CoverImageUpload(content=_png((1080, 1920)), kind="ai_image")
    )
    assert (out.width, out.height) == (1080, 1350)


def test_is_reel_ratio() -> None:
    assert is_reel_ratio(1080, 1920)
    assert not is_reel_ratio(1080, 1350)
    assert not is_reel_ratio(1080, 0)


# Scenario: A screenshot cannot be a reel cover
# Scenario: An unknown purpose is refused
@pytest.mark.parametrize(
    ("form", "problem"),
    [
        (CoverForm(kind="ai_image", source_url=None), None),
        (CoverForm(kind="ai_image", source_url=None, purpose="reel_cover"), None),
        (CoverForm(kind="ai_image", source_url=None, purpose=" carousel_cover "), None),
        (
            CoverForm(
                kind="screenshot",
                source_url="https://x.com/a/status/1",
                purpose="reel_cover",
            ),
            "asset_kind_invalid",
        ),
        (
            CoverForm(kind="ai_image", source_url=None, purpose="story_cover"),
            "asset_purpose_invalid",
        ),
        (
            CoverForm(kind="bad", source_url=None, purpose="reel_cover"),
            "asset_kind_invalid",
        ),
    ],
)
def test_form_problem(form: CoverForm, problem: str | None) -> None:
    assert form_problem(form) == problem


def test_form_purpose_default() -> None:
    assert form_purpose(CoverForm(kind="ai_image", source_url=None)) == "carousel_cover"


# Scenario: A topic cannot use a reel cover
def test_topic_refuses_a_reel_cover() -> None:
    cover = reel_cover()
    facts = CoverFacts(assets={cover.asset_id: cover}, now=NOW)
    assert (
        cover_reason(CoverCheck(asset_id=str(cover.asset_id), sources=()), facts)
        == "cover_asset_unknown"
    )


def test_repost_claim_marks_a_cover_used() -> None:
    assert reel_cover(repost_id=uuid4()).is_used
    assert not reel_cover().is_used


@dataclass
class _Images:
    seen: list[CoverImage] = field(default_factory=list)

    async def store_image(self, image: CoverImage) -> StoredImage:
        self.seen.append(image)
        return StoredImage(creator_asset_id=uuid4(), width=1080, height=1920)

    async def image_file(self, creator_asset_id: UUID) -> str | None:
        return None

    async def delete_images(self, creator_asset_ids: tuple[UUID, ...]) -> int:
        return 0


@dataclass
class _Covers:
    added: list[CoverAsset] = field(default_factory=list)

    async def add_cover(self, cover: CoverAsset) -> None:
        self.added.append(cover)

    async def commit(self) -> None:
        return None


async def test_upload_service_threads_the_purpose() -> None:
    images, covers = _Images(), _Covers()
    service = CoverUploadService(
        CoverUploadDependencies(
            covers=covers, images=images, clock=Clock(), owner_user_id="owner"
        )
    )
    result = await service.upload(
        CoverUploadCommand(
            content=b"x", kind="ai_image", source_url=None, purpose="reel_cover"
        )
    )
    assert result.purpose == "reel_cover"
    assert images.seen[0].purpose == "reel_cover"
    assert covers.added[0].purpose == "reel_cover"
    default = await service.upload(
        CoverUploadCommand(content=b"x", kind="ai_image", source_url=None)
    )
    assert default.purpose == "carousel_cover"
    with pytest.raises(CoverAssetError) as error:
        await service.upload(
            CoverUploadCommand(
                content=b"x", kind="ai_image", source_url=None, purpose="x"
            )
        )
    assert error.value.code == "asset_purpose_invalid"
