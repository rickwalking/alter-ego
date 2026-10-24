"""Grok cover generation: the reference-photo encoder, the picker and the task.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature). Fakes for every port; the
photos are generated images.
"""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass, field

import pytest
from PIL import Image
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.cover_generation_tasks import (
    running_cover_generation_tasks,
    schedule_cover_generation,
)
from rag_backend.application.services.carousel.cover_pick import (
    CoverPickCommand,
    CoverPickDeps,
    CoverPickService,
)
from rag_backend.application.services.carousel.reference_photo import reference_photo
from rag_backend.application.services.carousel.slide_cover_switch import (
    SlideCoverSwitchCommand,
    SlideCoverSwitchResult,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.domain.models.slide_cover import CoverAssetError, SlideCover

_OWNER = "00000000-0000-4000-8000-000000000508"


def _project() -> CarouselProject:
    project = CarouselProject(topic="T", audience="Devs", niche="IA")
    project.owner_id = _OWNER
    project.content_mode = "pov"
    project.status = CarouselStatus.COMPLETED
    project.phase_status = "awaiting_human"
    return project


class TestReferencePhoto:
    def test_drops_metadata_and_bounds_the_size(self) -> None:
        """Scenario: A confirmed generation links the photos and stores a private cover."""
        source = io.BytesIO()
        image = Image.new("RGB", (2000, 3000), (10, 20, 30))
        exif = Image.Exif()
        exif[0x010F] = "SecretCam"
        image.save(source, format="JPEG", exif=exif.tobytes())

        photo = reference_photo(source.getvalue())

        assert photo.mime_type == "image/png"
        with Image.open(io.BytesIO(photo.content)) as sent:
            assert sent.format == "PNG"
            assert max(sent.size) == 1024
            assert not sent.getexif()
        assert b"SecretCam" not in photo.content

    def test_unreadable_bytes_are_refused(self) -> None:
        """Scenario: A bridge failure leaves no asset and can be retried."""
        with pytest.raises(CoverAssetError):
            reference_photo(b"not an image")


@dataclass
class _Library:
    async def photos(self, owner_id: str) -> tuple[CarouselCreatorAsset, ...]:
        del owner_id
        return ()

    async def stage(
        self, project: CarouselProject, asset: CarouselCreatorAsset
    ) -> None:
        del project, asset


@dataclass
class _NoOffer:
    async def offer(self, project_id: str) -> SlideCover | None:
        del project_id


@dataclass
class _Switcher:
    commands: list[SlideCoverSwitchCommand] = field(default_factory=list)

    async def switch(self, command: SlideCoverSwitchCommand) -> SlideCoverSwitchResult:
        self.commands.append(command)
        return SlideCoverSwitchResult(status="fixed")


@dataclass
class _Generated:
    items: tuple[CarouselCreatorAsset, ...]

    async def covers(self, project_id: str) -> tuple[CarouselCreatorAsset, ...]:
        del project_id
        return self.items


class TestPicker:
    async def test_generated_cover_is_offered_and_picked_as_ai_image(self) -> None:
        """Scenario: The generated cover is a cover option and can be picked."""
        made = CarouselCreatorAsset(
            owner_id=_OWNER,
            content_sha256="abc",
            media_type="image/webp",
            width=1080,
            height=1350,
            relative_path="assets/creators/abc.webp",
            role="cover",
        )
        switcher = _Switcher()
        service = CoverPickService(
            CoverPickDeps(
                library=_Library(),
                offers=_NoOffer(),
                switcher=switcher,
                generated=_Generated((made,)),
            )
        )
        project = _project()

        options = await service.options(project)
        await service.pick(
            CoverPickCommand(project=project, asset_id=made.id, expected_version=3)
        )

        assert [(o.asset_id, o.source, o.kind) for o in options.options] == [
            (made.id, "generated", "ai_image")
        ]
        cover = switcher.commands[0].cover
        assert cover == SlideCover(
            asset_id=made.id, kind="ai_image", staged_path="assets/creators/abc.webp"
        )
        assert switcher.commands[0].hook_photo is None

    async def test_picker_without_generated_source_lists_none(self) -> None:
        """Scenario: The generated cover is a cover option and can be picked."""
        service = CoverPickService(
            CoverPickDeps(library=_Library(), offers=_NoOffer(), switcher=_Switcher())
        )
        assert (await service.options(_project())).options == ()


async def test_a_crashed_run_is_logged_and_untracked() -> None:
    """Scenario: A run lost to a restart is reported as interrupted."""

    async def _boom() -> object:
        raise ValueError("db down")

    with capture_logs() as logs:
        task = schedule_cover_generation(_boom, "gen-1")
        assert task in running_cover_generation_tasks()
        assert task.get_name() == "cover-generation-gen-1"
        await task
        await asyncio.sleep(0)

    assert task not in running_cover_generation_tasks()
    assert logs[0]["event"] == "cover_generation_crashed"
    assert logs[0]["generation_id"] == "gen-1"


def test_a_heavy_photo_is_scaled_under_the_byte_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: A confirmed generation links the photos and stores a private cover."""
    import os

    from rag_backend.application.services.carousel import reference_photo as module

    noise = Image.frombytes("RGB", (1200, 1200), os.urandom(1200 * 1200 * 3))
    source = io.BytesIO()
    noise.save(source, format="PNG")
    monkeypatch.setattr(module, "REFERENCE_PHOTO_MAX_BYTES", 1_000_000)

    photo = module.reference_photo(source.getvalue())

    assert len(photo.content) <= 1_000_000
    with Image.open(io.BytesIO(photo.content)) as sent:
        assert max(sent.size) == 512


def test_a_photo_too_heavy_even_small_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: A bridge failure leaves no asset and can be retried."""
    from rag_backend.application.services.carousel import reference_photo as module

    source = io.BytesIO()
    Image.new("RGB", (800, 800), (1, 2, 3)).save(source, format="PNG")
    monkeypatch.setattr(module, "REFERENCE_PHOTO_MAX_BYTES", 10)

    with pytest.raises(CoverAssetError):
        module.reference_photo(source.getvalue())
