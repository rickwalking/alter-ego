"""The GrokBot cover offered to a carousel's autopilot run, by project.

Gherkin: tests/features/carousel_cover_pick_ae0445.feature
  Scenario: The GrokBot cover offer of the autopilot run is an option too
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.modules.autopilot import project_cover_offer
from rag_backend.modules.autopilot.domain.cover import CoverAsset
from rag_backend.modules.autopilot.domain.cover_ports import CoverImage
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
)
from rag_backend.modules.autopilot.infrastructure.cover_images import (
    EditorialCoverImages,
)
from rag_backend.modules.autopilot.infrastructure.cover_store import SqlCoverAssetStore
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)

_OWNER = "00000000-0000-4000-8000-000000000445"


def _png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (1080, 1350), (4, 4, 5)).save(buffer, format="PNG")
    return buffer.getvalue()


async def _cover(session: AsyncSession) -> CoverAsset:
    session.add(
        UserModel(
            id=_OWNER,
            email="pick@example.com",
            full_name="Owner",
            hashed_password="hash",
            role=UserRole.EDITOR.value,
        )
    )
    await session.flush()
    stored = await EditorialCoverImages(session).store_image(
        CoverImage(owner_id=_OWNER, content=_png(), kind="ai_image")
    )
    cover = CoverAsset(
        asset_id=uuid4(),
        creator_asset_id=stored.creator_asset_id,
        kind="ai_image",
        source_url=None,
        width=1080,
        height=1350,
        created_at=datetime(2026, 10, 20, tzinfo=UTC),
    )
    store = SqlCoverAssetStore(session)
    await store.add_cover(cover)
    await store.commit()
    return cover


async def _run(
    session: AsyncSession, cover: CoverAsset | None, project_id: str
) -> None:
    repo = SqlAlchemyAutopilotRepository(session)
    topic = TopicCandidate(
        candidate_id=uuid4(),
        title="Agents ship",
        angle="a",
        why_viral="w",
        audience="devs",
        niche="ai",
        brief="b",
        sources=("https://example.com/a",),
        score=80,
        signal_hash=uuid4().hex,
        status="accepted",
        content_mode="pov",
        cover_asset_id=cover.asset_id if cover is not None else None,
    )
    await repo.add_topic(topic)
    run = AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=topic.candidate_id,
        carousel_project_id=None,
        state=AutopilotRunState.AWAITING_OWNER,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )
    await repo.add(replace(run, carousel_project_id=project_id))


@pytest.mark.asyncio
async def test_offer_by_project_unchosen_and_gone(
    db_session: AsyncSession, asset_dirs: Path
) -> None:
    cover = await _cover(db_session)
    project_id = str(uuid4())
    await _run(db_session, cover, project_id)
    offers = project_cover_offer(db_session)

    found = await offers.offer(project_id)

    assert found is not None
    assert (found.asset_id, found.kind) == (cover.creator_asset_id, "ai_image")
    assert found.staged_path.startswith("assets/creators/")
    assert await offers.offer(str(uuid4())) is None
    path = await EditorialCoverImages(db_session).image_file(cover.creator_asset_id)
    assert path is not None
    Path(path).unlink()
    assert await offers.offer(project_id) is None


@pytest.mark.asyncio
async def test_no_offer_when_the_topic_has_no_cover(
    db_session: AsyncSession, asset_dirs: Path
) -> None:
    project_id = str(uuid4())
    await _run(db_session, None, project_id)
    assert await project_cover_offer(db_session).offer(project_id) is None
