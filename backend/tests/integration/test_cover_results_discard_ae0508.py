"""``EditorialCoverResults``: storing a generated cover and discarding it.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature). The real adapter over the
in-memory database and a temporary asset folder; images are generated. The
asset store commits a stored result, so a result whose settle fails is
discarded (row and file) rather than rolled back.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from rag_backend.domain.models import UserRole
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.modules.editorial.infrastructure.carousel_cover_generation import (
    EditorialCoverResults,
)
from tests.integration.conftest import create_test_user
from tests.integration.cover_generation_support import cover_png


def _stored_files(asset_dirs: Path) -> list[Path]:
    return sorted((asset_dirs / "assets").glob("*.webp"))


async def _owner_id(client: AsyncClient) -> str:
    me = await client.get("/api/auth/me")
    assert me.status_code == 200, me.text
    return str(me.json()["id"])


async def _row_exists(asset_id: UUID) -> bool:
    from rag_backend.infrastructure.database.models import CarouselCreatorAssetModel

    async with get_session_maker()() as session:
        return await session.get(CarouselCreatorAssetModel, str(asset_id)) is not None


async def _store(owner_id: str, image: bytes) -> UUID:
    async with get_session_maker()() as session:
        asset_id = await EditorialCoverResults(session).store(owner_id, image)
        await session.commit()
        return asset_id


async def _discard(asset_id: UUID) -> None:
    async with get_session_maker()() as session:
        await EditorialCoverResults(session).discard(asset_id)
        await session.commit()


@pytest.mark.integration
class TestDiscard:
    async def test_a_stored_result_survives_a_rollback(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: A bridge failure leaves no asset and can be retried."""
        owner = await _owner_id(client)
        async with get_session_maker()() as session:
            asset_id = await EditorialCoverResults(session).store(owner, cover_png())
            await session.rollback()

        assert await _row_exists(asset_id)
        assert len(_stored_files(asset_dirs)) == 1

    async def test_discard_removes_the_row_and_the_file(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: A bridge failure leaves no asset and can be retried."""
        owner = await _owner_id(client)
        asset_id = await _store(owner, cover_png())

        await _discard(asset_id)

        assert not await _row_exists(asset_id)
        assert _stored_files(asset_dirs) == []

    async def test_bytes_another_owner_still_uses_are_kept(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: A bridge failure leaves no asset and can be retried."""
        owner = await _owner_id(client)
        other = await create_test_user(f"{uuid4().hex}@x.test", UserRole.EDITOR)
        image = cover_png()
        kept = await _store(str(other.id), image)
        dropped = await _store(owner, image)

        await _discard(dropped)

        assert dropped != kept
        assert not await _row_exists(dropped)
        assert await _row_exists(kept)
        assert len(_stored_files(asset_dirs)) == 1

    async def test_an_unknown_result_is_a_no_op(
        self, client: AsyncClient, asset_dirs: Path
    ) -> None:
        """Scenario: A bridge failure leaves no asset and can be retried."""
        owner = await _owner_id(client)
        asset_id = await _store(owner, cover_png())

        await _discard(uuid4())

        assert await _row_exists(asset_id)
        assert len(_stored_files(asset_dirs)) == 1
