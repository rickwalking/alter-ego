"""PR #136 review fixes over SQL: shared images and a failed re-render.

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
  Scenario: Sweeping an unused cover keeps a used cover with the same bytes
  Scenario: The sweep keeps an image a carousel still renders
  Scenario: A failed slide-1 re-render is escalated, never reported as done
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel import slide_cover_switch
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.infrastructure.database.creator_asset_repository import (
    PostgresCreatorAssetRepository,
)
from rag_backend.modules.autopilot.application.cover_sweep import (
    CoverSweepDependencies,
    CoverSweepService,
)
from rag_backend.modules.autopilot.domain.cover import CoverAsset
from rag_backend.modules.autopilot.domain.cover_ports import (
    CoverClaim,
    CoverSwitchCommand,
    CoverSwitchStatus,
)
from rag_backend.modules.autopilot.infrastructure.cover_images import (
    EditorialCoverImages,
    EditorialCoverSwitcher,
)
from rag_backend.modules.autopilot.infrastructure.cover_store import SqlCoverAssetStore
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.editorial.infrastructure import carousel_owner_autofix
from rag_backend.modules.editorial.public import CarouselAutomationAcl
from tests.integration.test_cover_seam_ae0418 import (
    _NOW,
    _cover,
    _no_lock,
    _project,
    _seed_owner,
    _topic,
)

_OLD = timedelta(hours=7)


class _Clock:
    def now(self) -> datetime:
        return _NOW


def _sweep(session: AsyncSession) -> CoverSweepService:
    return CoverSweepService(
        CoverSweepDependencies(
            covers=SqlCoverAssetStore(session),
            images=EditorialCoverImages(session),
            clock=_Clock(),
        )
    )


async def _file(session: AsyncSession, cover: CoverAsset) -> Path | None:
    path = await EditorialCoverImages(session).image_file(cover.creator_asset_id)
    return Path(path) if path is not None else None


# Scenario: Sweeping an unused cover keeps a used cover with the same bytes
@pytest.mark.asyncio
async def test_sweep_keeps_a_used_cover_with_the_same_bytes(
    db_session: AsyncSession, asset_dirs: Path
) -> None:
    await _seed_owner(db_session)
    unused = await _cover(db_session, age=_OLD)
    used = await _cover(db_session, age=_OLD)
    assert used.creator_asset_id == unused.creator_asset_id
    topic = _topic(used.asset_id)
    await SqlAlchemyAutopilotRepository(db_session).add_topic(topic)
    store = SqlCoverAssetStore(db_session)
    claim = CoverClaim(asset_id=used.asset_id, topic_candidate_id=topic.candidate_id)
    assert await store.claim_cover(claim)
    await store.commit()

    assert await _sweep(db_session).tick() == 1

    left = await store.covers_by_ids((unused.asset_id, used.asset_id))
    assert list(left) == [used.asset_id]
    assert left[used.asset_id].topic_candidate_id == topic.candidate_id
    path = await _file(db_session, used)
    assert path is not None and path.is_file()


# Scenario: The sweep keeps an image a carousel still renders
@pytest.mark.asyncio
async def test_sweep_keeps_an_image_a_project_renders(
    db_session: AsyncSession, asset_dirs: Path
) -> None:
    await _seed_owner(db_session)
    cover = await _cover(db_session, age=_OLD)
    slide = SlideCover(
        asset_id=cover.creator_asset_id, kind="ai_image", staged_path="a/b.webp"
    )
    acl = CarouselAutomationAcl(db_session)
    await acl.create_project(await _project(db_session, slide, asset_dirs / "o"))
    lone = await _cover(db_session, age=_OLD, shade=30)

    assert await _sweep(db_session).tick() == 2

    assets = PostgresCreatorAssetRepository(db_session)
    assert await assets.get_by_id(cover.creator_asset_id) is not None
    assert await assets.get_by_id(lone.creator_asset_id) is None
    path = await _file(db_session, cover)
    assert path is not None and path.is_file()


# Scenario: A failed slide-1 re-render is escalated, never reported as done
@pytest.mark.asyncio
async def test_switch_with_render_errors_is_not_switched(
    db_session: AsyncSession, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _seed_owner(db_session)
    cover = await _cover(db_session)
    acl = CarouselAutomationAcl(db_session)
    project_id = await acl.create_project(
        await _project(db_session, None, asset_dirs / "out-fail")
    )

    async def _render(_self: object, project: str) -> tuple[str, ...]:
        del project
        return ("slide_1_render_failed",)

    monkeypatch.setattr(slide_cover_switch, "write_locked", _no_lock([]))
    monkeypatch.setattr(carousel_owner_autofix.RepublishRenderer, "render", _render)
    slide = SlideCover(
        asset_id=cover.creator_asset_id, kind="ai_image", staged_path=cover.staged_path
    )
    status = await EditorialCoverSwitcher(db_session).switch(
        CoverSwitchCommand(project_id=project_id, expected_version=1, cover=slide)
    )
    assert status is CoverSwitchStatus.RENDER_FAILED
