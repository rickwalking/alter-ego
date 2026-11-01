"""The editorial side of a Grok cover generated from the owner's photos.

``EditorialOwnerPhotos`` lists and re-encodes the owner's library photos;
``EditorialCoverResults`` stores the generated image with the GrokBot
``ai_image`` cover rules (role ``cover``, private) or discards it;
``EditorialGeneratedCovers`` lists a carousel's generated covers for the
picker. Each works on the session it is given: the request's, or a fresh one
for the background run.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.cover_generation import (
    COVER_GENERATION_GRACE_SECONDS,
    FAILURE_PHOTO_UNREADABLE,
)
from rag_backend.domain.constants.slide_cover import (
    COVER_KIND_AI_IMAGE,
)
from rag_backend.domain.models.carousel_creator_asset import CarouselCreatorAsset
from rag_backend.domain.models.cover_generation import (
    CoverGenerationStatus,
    ReferencePhoto,
)
from rag_backend.domain.models.slide_cover import CoverAssetError
from rag_backend.domain.protocols import CoverImageEditor
from rag_backend.modules.editorial.infrastructure.carousel_cover import (
    CoverImageRequest,
    delete_cover_images,
    store_cover_image,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_pick import (
    EditorialCoverLibrary,
)
from rag_backend.modules.editorial.infrastructure.pov_inputs import (
    creator_asset_service,
    creator_assets,
)

if TYPE_CHECKING:
    from rag_backend.application.services.carousel.cover_generation import (
        CoverGenerationConfig,
        CoverGenerationRun,
        CoverGenerationService,
    )
    from rag_backend.application.services.carousel.cover_generation_runner import (
        CoverGenerationRunner,
    )


class EditorialOwnerPhotos:
    """``OwnerPhotos`` over the creator-asset rows and files of one session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def photo_ids(self, owner_id: str) -> frozenset[UUID]:
        """The owner's slide-1 photos whose stored file exists."""
        photos = await EditorialCoverLibrary(self._session).photos(owner_id)
        return frozenset(photo.id for photo in photos)

    async def load(self, asset_ids: tuple[UUID, ...]) -> tuple[ReferencePhoto, ...]:
        """Each photo re-encoded as a metadata-free PNG, in order."""
        photos = [await self._one(asset_id) for asset_id in asset_ids]
        return tuple(photos)

    async def _one(self, asset_id: UUID) -> ReferencePhoto:
        from rag_backend.application.services.carousel.reference_photo import (
            reference_photo,
        )

        asset = await creator_assets(self._session).get_by_id(asset_id)
        path = (
            creator_asset_service(self._session).stored_file(asset)
            if asset is not None
            else None
        )
        if path is None:
            raise CoverAssetError(FAILURE_PHOTO_UNREADABLE)
        try:
            content = await asyncio.to_thread(Path.read_bytes, path)
        except OSError:
            raise CoverAssetError(FAILURE_PHOTO_UNREADABLE) from None
        return await asyncio.to_thread(reference_photo, content)


class EditorialCoverResults:
    """``CoverResults``: the generated image as a private ``cover`` asset."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store(self, owner_id: str, image: bytes) -> UUID:
        """Validate (``ai_image`` rules), re-encode and store; the asset id.

        The asset store commits the new row.
        """
        stored = await store_cover_image(
            CoverImageRequest(
                session=self._session,
                owner_id=owner_id,
                content=image,
                kind=COVER_KIND_AI_IMAGE,
            )
        )
        return stored.creator_asset_id

    async def discard(self, asset_id: UUID) -> None:
        """Delete a stored result (row and file) no generation will reference.

        The file is kept while another creator asset points at the same bytes;
        the caller commits.
        """
        await delete_cover_images(self._session, (asset_id,))


async def cover_generation_input(
    session: AsyncSession, generation_id: UUID, index: int
) -> bytes | None:
    """Photo ``index`` of a pending generation, re-encoded on each request.

    None when the generation is unknown or settled, the index is out of range,
    or the photo (one of the owner's own library photos) is gone or unreadable.
    No copy is stored; the bytes are the same metadata-free PNG the run checked.
    """
    from rag_backend.modules.editorial.infrastructure.cover_generations import (
        SqlCoverGenerationRepository,
    )

    generation = await SqlCoverGenerationRepository(session).get(generation_id)
    if generation is None or generation.status is not CoverGenerationStatus.PENDING:
        return None
    if not 0 <= index < len(generation.photo_ids):
        return None
    asset_id = generation.photo_ids[index]
    if asset_id not in await EditorialOwnerPhotos(session).photo_ids(
        generation.owner_id
    ):
        return None
    try:
        (photo,) = await EditorialOwnerPhotos(session).load((asset_id,))
    except CoverAssetError:
        return None
    return photo.content


class EditorialGeneratedCovers:
    """``GeneratedCoverSource``: succeeded generations whose image still exists."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def covers(self, project_id: str) -> tuple[CarouselCreatorAsset, ...]:
        """The carousel's generated covers, newest first."""
        from rag_backend.infrastructure.database.models import (
            CarouselCoverGenerationModel as Row,
        )

        ids = await self._session.scalars(
            select(Row.result_asset_id)
            .where(
                Row.project_id == project_id,
                Row.status == CoverGenerationStatus.SUCCEEDED.value,
                Row.result_asset_id.is_not(None),
            )
            .order_by(Row.created_at.desc(), Row.id)
        )
        service = creator_asset_service(self._session)
        repo = creator_assets(self._session)
        found: list[CarouselCreatorAsset] = []
        for asset_id in ids:
            asset = await repo.get_by_id(UUID(str(asset_id)))
            if asset is not None and service.has_stored_file(asset):
                found.append(asset)
        return tuple(found)


@dataclass(frozen=True, kw_only=True)
class CoverRunWiring:
    """The bridge editor, the prompt template and the clock of a background run."""

    editor: CoverImageEditor
    render_prompt: Callable[[str], str]
    now: Callable[[], datetime]


def utc_now() -> datetime:
    """The current time, timezone-aware UTC."""
    return datetime.now(UTC)


def cover_generation_config() -> CoverGenerationConfig:
    """The model and cost recorded per generation, and when a run is lost."""
    from rag_backend.application.services.carousel.cover_generation import (
        CoverGenerationConfig,
    )
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.modules.image_bridge import IMAGE_BRIDGE_MODEL

    settings = get_settings()
    return CoverGenerationConfig(
        model=IMAGE_BRIDGE_MODEL,
        cost_usd=settings.grok_cover_cost_usd,
        stale_after_seconds=settings.image_bridge_timeout_seconds
        + COVER_GENERATION_GRACE_SECONDS,
        now=utc_now,
    )


def cover_generation_service(session: AsyncSession) -> CoverGenerationService:
    """Usage and start of a generation on the request's session."""
    from rag_backend.application.services.carousel.cover_generation import (
        CoverGenerationService,
    )
    from rag_backend.modules.editorial.infrastructure.cover_generations import (
        SqlCoverGenerationRepository,
    )

    return CoverGenerationService(
        SqlCoverGenerationRepository(session),
        EditorialOwnerPhotos(session),
        cover_generation_config(),
    )


_shared_editor: list[tuple[object, CoverImageEditor]] = []


def _cover_editor() -> CoverImageEditor:
    """One bridge editor per settings object, so every cover job shares its slots.

    Raises ``ImageBridgeConfigError`` when the bridge is not configured (never
    cached, so configuring it takes effect on the next request).
    """
    from rag_backend.infrastructure.config.settings import get_settings
    from rag_backend.modules.image_bridge import build_grokbot_cover_editor

    settings = get_settings()
    if _shared_editor and _shared_editor[0][0] is settings:
        return _shared_editor[0][1]
    editor = build_grokbot_cover_editor(settings)
    _shared_editor[:] = [(settings, editor)]
    return editor


def cover_run_wiring(render_prompt: Callable[[str], str]) -> CoverRunWiring:
    """The bridge editor (no OpenAI fallback), the prompt and the clock.

    Raises ``ImageBridgeConfigError`` when the bridge is not configured, so the
    caller refuses before anything is recorded.
    """
    return CoverRunWiring(
        editor=_cover_editor(), render_prompt=render_prompt, now=utc_now
    )


def cover_generation_runner(
    session: AsyncSession, wiring: CoverRunWiring
) -> CoverGenerationRunner:
    """One background run on the given session."""
    from rag_backend.application.services.carousel.cover_generation_runner import (
        CoverGenerationRunner,
        CoverRunDeps,
    )
    from rag_backend.modules.editorial.infrastructure.cover_generations import (
        SqlCoverGenerationRepository,
    )

    return CoverGenerationRunner(
        CoverRunDeps(
            store=SqlCoverGenerationRepository(session),
            photos=EditorialOwnerPhotos(session),
            results=EditorialCoverResults(session),
            editor=wiring.editor,
            render_prompt=wiring.render_prompt,
            now=wiring.now,
        )
    )


def cover_generation_task(
    wiring: CoverRunWiring, run: CoverGenerationRun
) -> Callable[[], Awaitable[CoverGenerationStatus]]:
    """The background run of ``run`` on its own session."""
    from rag_backend.infrastructure.database.config import get_session_maker

    async def _execute() -> CoverGenerationStatus:
        async with get_session_maker()() as session:
            return await cover_generation_runner(session, wiring).run(run)

    return _execute


__all__ = [
    "CoverRunWiring",
    "EditorialCoverResults",
    "EditorialGeneratedCovers",
    "EditorialOwnerPhotos",
    "cover_generation_config",
    "cover_generation_input",
    "cover_generation_runner",
    "cover_generation_service",
    "cover_generation_task",
    "cover_run_wiring",
    "utc_now",
]
