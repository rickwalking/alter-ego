"""The slide-1 photo chosen at create time (PR #106 review, item 4).

Gherkin: tests/features/carousel_content_mode.feature ("Slide-1 photo on create")
"""

from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from rag_backend.api.routes.carousels.create_hook_photo import (
    bind_hook_photo,
    check_hook_photo,
)
from rag_backend.api.schemas.carousel import CarouselProjectCreate
from rag_backend.application.services.carousel.creator_asset_service import (
    CreatorAssetService,
    HookPhotoCommand,
)
from rag_backend.application.services.carousel.creator_asset_validation import (
    CreatorAssetValidationError,
)
from rag_backend.domain.models import CarouselProject, User, UserRole

_FORBIDDEN = "creator_asset_forbidden"


class _Service:
    def __init__(self, error: str = "") -> None:
        self.error = error
        self.checked: list[UUID] = []
        self.bound: list[HookPhotoCommand] = []

    async def library_image_path(self, user: User, asset_id: UUID) -> object:
        self.checked.append(asset_id)
        if self.error:
            raise CreatorAssetValidationError(self.error)
        return object()

    async def select_hook_photo(self, command: HookPhotoCommand) -> CarouselProject:
        self.bound.append(command)
        if self.error:
            raise CreatorAssetValidationError(self.error)
        return command.project


def _user() -> User:
    return User(
        email="e@x.test", full_name="E", role=UserRole.EDITOR, hashed_password="x"
    )


def _service(fake: _Service) -> CreatorAssetService:
    return cast(CreatorAssetService, fake)


@pytest.mark.unit
class TestCheck:
    @pytest.mark.asyncio
    async def test_radar_ia_skips_the_check(self) -> None:
        fake = _Service()
        request = CarouselProjectCreate(topic="T", audience="A", niche="N")
        await check_hook_photo(_service(fake), _user(), request)
        assert fake.checked == []

    @pytest.mark.asyncio
    async def test_foreign_photo_is_403(self) -> None:
        photo = uuid4()
        fake = _Service(error=_FORBIDDEN)
        request = CarouselProjectCreate(
            topic="T",
            audience="A",
            niche="N",
            content_mode="pov",
            pov_thesis="Tese",
            hook_asset_id=photo,
        )
        with pytest.raises(HTTPException) as caught:
            await check_hook_photo(_service(fake), _user(), request)
        assert caught.value.status_code == 403
        assert fake.checked == [photo]


@pytest.mark.unit
class TestBind:
    @pytest.mark.asyncio
    async def test_no_photo_is_a_no_op(self) -> None:
        fake = _Service()
        project = CarouselProject(topic="T", audience="A", niche="N")
        assert await bind_hook_photo(_service(fake), project, _user()) is project
        assert fake.bound == []

    @pytest.mark.asyncio
    async def test_binds_into_the_output_root(self, tmp_path: object) -> None:
        fake = _Service()
        photo = uuid4()
        project = CarouselProject(
            topic="T",
            audience="A",
            niche="N",
            hook_asset_id=photo,
            output_dir=str(tmp_path),
        )
        await bind_hook_photo(_service(fake), project, _user())
        (command,) = fake.bound
        assert command.creator_asset_id == photo
        assert str(command.output_root) == str(tmp_path)

    @pytest.mark.asyncio
    async def test_a_late_refusal_maps_to_http(self) -> None:
        fake = _Service(error="creator_asset_not_found")
        project = CarouselProject(
            topic="T", audience="A", niche="N", hook_asset_id=uuid4()
        )
        with pytest.raises(HTTPException) as caught:
            await bind_hook_photo(_service(fake), project, _user())
        assert caught.value.status_code == 400
