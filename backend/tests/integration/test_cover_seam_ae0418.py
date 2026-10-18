"""The GrokBot cover seam over SQL and the creator-asset storage (AE-0418).

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
  Scenario: "Usar capa do Grok" at the thesis switches slide 1 to the cover
  Scenario: The Radar IA review offers the cover and swaps slide 1
  Scenario: Unused covers older than 6 hours are deleted
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel import slide_cover_switch
from rag_backend.application.services.carousel.owner_autofix_lock import (
    AutofixConflictError,
    LockedWrite,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.slide_cover import CoverAssetError, SlideCover
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.creator_asset_repository import (
    PostgresCreatorAssetRepository,
)
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.modules.autopilot.domain.cover import CoverAsset
from rag_backend.modules.autopilot.domain.cover_ports import (
    CoverChoiceCommand,
    CoverClaim,
    CoverImage,
    CoverSwitchCommand,
    CoverSwitchStatus,
    ExpiredCoverQuery,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
)
from rag_backend.modules.autopilot.infrastructure.cover_images import (
    EditorialCoverImages,
    EditorialCoverSwitcher,
)
from rag_backend.modules.autopilot.infrastructure.cover_offers import (
    SqlCoverChoices,
    cover_offers,
)
from rag_backend.modules.autopilot.infrastructure.cover_store import SqlCoverAssetStore
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.editorial.infrastructure import carousel_owner_autofix
from rag_backend.modules.editorial.public import CarouselAutomationAcl

_OWNER = "00000000-0000-4000-8000-000000000418"
_NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
_X = "https://x.com/poteto/status/2111133080526495985"


def _png(size: tuple[int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (9, 9, 9)).save(buffer, format="PNG")
    return buffer.getvalue()


async def _seed_owner(session: AsyncSession) -> None:
    session.add(
        UserModel(
            id=_OWNER,
            email="cover@example.com",
            full_name="Owner",
            hashed_password="hash",
            role=UserRole.EDITOR.value,
        )
    )
    await session.flush()


async def _image(session: AsyncSession, kind: str = "ai_image") -> UUID:
    stored = await EditorialCoverImages(session).store_image(
        CoverImage(owner_id=_OWNER, content=_png((1080, 1350)), kind=kind)
    )
    return stored.creator_asset_id


async def _cover(
    session: AsyncSession,
    *,
    age: timedelta = timedelta(hours=1),
    kind: str = "ai_image",
) -> CoverAsset:
    cover = CoverAsset(
        asset_id=uuid4(),
        creator_asset_id=await _image(session, kind),
        kind=kind,
        source_url=_X if kind == "screenshot" else None,
        width=1080,
        height=1350,
        created_at=_NOW - age,
    )
    store = SqlCoverAssetStore(session)
    await store.add_cover(cover)
    await store.commit()
    return cover


def _topic(cover_id: UUID | None) -> TopicCandidate:
    return TopicCandidate(
        candidate_id=uuid4(),
        title="Agents ship",
        angle="a",
        why_viral="w",
        audience="devs",
        niche="ai",
        brief="b",
        sources=(_X,),
        score=80,
        signal_hash=uuid4().hex,
        status="accepted",
        content_mode="pov",
        cover_asset_id=cover_id,
    )


def _run(topic: TopicCandidate, state: AutopilotRunState) -> AutopilotRun:
    return AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=topic.candidate_id,
        carousel_project_id=None,
        state=state,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )


@pytest.mark.asyncio
async def test_store_claim_expire_and_sweep(
    db_session: AsyncSession, asset_dirs: Path
) -> None:
    await _seed_owner(db_session)
    fresh = await _cover(db_session)
    old = await _cover(db_session, age=timedelta(hours=7))
    store = SqlCoverAssetStore(db_session)
    found = await store.covers_by_ids((fresh.asset_id, uuid4()))
    assert list(found) == [fresh.asset_id]
    assert found[fresh.asset_id].staged_path.startswith("assets/creators/")
    assert await store.covers_by_ids(()) == {}

    repo = SqlAlchemyAutopilotRepository(db_session)
    topic = _topic(fresh.asset_id)
    await repo.add_topic(topic)
    claim = CoverClaim(asset_id=fresh.asset_id, topic_candidate_id=topic.candidate_id)
    assert await store.claim_cover(claim)
    assert not await store.claim_cover(claim)

    expired = await store.expired_covers(
        ExpiredCoverQuery(before=_NOW - timedelta(hours=6), limit=10)
    )
    assert [c.asset_id for c in expired] == [old.asset_id]

    images = EditorialCoverImages(db_session)
    path = await images.image_file(old.creator_asset_id)
    assert path is not None and Path(path).is_file()
    await store.delete_covers((old.asset_id,))
    assert await images.delete_images((old.creator_asset_id, uuid4())) == 1
    await store.commit()
    assert not Path(path).exists()
    assert await images.image_file(old.creator_asset_id) is None
    await store.delete_covers(())


@pytest.mark.asyncio
async def test_owner_photo_with_the_same_bytes_is_never_deleted(
    db_session: AsyncSession, asset_dirs: Path
) -> None:
    await _seed_owner(db_session)
    assets = PostgresCreatorAssetRepository(db_session)
    creator_id = await _image(db_session)
    asset = await assets.get_by_id(creator_id)
    assert asset is not None and asset.role == "cover"
    # Same bytes again: the existing row is reused (no second row, role kept).
    assert await _image(db_session) == creator_id
    # An owner photo is not a cover: the sweep keeps it.
    from rag_backend.domain.models.carousel_creator_asset import CreatorAssetTags

    await assets.set_tags(CreatorAssetTags(asset_id=creator_id, role="hook"))
    assert await EditorialCoverImages(db_session).delete_images((creator_id,)) == 0


@pytest.mark.asyncio
async def test_invalid_image_raises_the_contract_code(
    db_session: AsyncSession, asset_dirs: Path
) -> None:
    with pytest.raises(CoverAssetError) as raised:
        await EditorialCoverImages(db_session).store_image(
            CoverImage(owner_id=_OWNER, content=_png((700, 700)), kind="ai_image")
        )
    assert raised.value.code == "asset_too_small"


@pytest.mark.asyncio
async def test_offer_choice_and_chosen_cover(
    db_session: AsyncSession, asset_dirs: Path
) -> None:
    await _seed_owner(db_session)
    shot = await _cover(db_session, kind="screenshot")
    repo = SqlAlchemyAutopilotRepository(db_session)
    topic = _topic(shot.asset_id)
    await repo.add_topic(topic)
    run = _run(topic, AutopilotRunState.AWAITING_THESIS)
    await repo.add(run)
    offers = cover_offers(db_session)

    offer = await offers.offer(run)
    assert offer is not None
    assert (offer.kind, offer.credit, offer.chosen, offer.pov) == (
        "screenshot",
        "@poteto · X",
        False,
        True,
    )
    assert await offers.chosen_cover(run) is None

    choices = SqlCoverChoices(db_session)
    wrong = CoverChoiceCommand(
        run_id=run.run_id, expected=AutopilotRunState.QUEUED, chosen=True
    )
    assert not await choices.set_cover_choice(wrong)
    right = CoverChoiceCommand(
        run_id=run.run_id, expected=AutopilotRunState.AWAITING_THESIS, chosen=True
    )
    assert await choices.set_cover_choice(right)
    stored = await repo.get(run.run_id)
    assert stored is not None and stored.cover_chosen
    cover = await offers.chosen_cover(stored)
    assert cover is not None
    assert (cover.asset_id, cover.kind, cover.credit) == (
        shot.creator_asset_id,
        "screenshot",
        "@poteto · X",
    )


@pytest.mark.asyncio
async def test_no_offer_without_a_usable_cover(
    db_session: AsyncSession, asset_dirs: Path
) -> None:
    await _seed_owner(db_session)
    repo = SqlAlchemyAutopilotRepository(db_session)
    plain = _topic(None)
    ghost = _topic(uuid4())
    for topic in (plain, ghost):
        await repo.add_topic(topic)
    offers = cover_offers(db_session)
    for topic in (plain, ghost):
        run = _run(topic, AutopilotRunState.AWAITING_OWNER)
        assert await offers.offer(run) is None
        chosen = replace(run, cover_chosen=True)
        assert await offers.chosen_cover(chosen) is None
    missing_topic = _run(_topic(None), AutopilotRunState.AWAITING_OWNER)
    assert await offers.offer(missing_topic) is None
    # The stored file is gone: no offer (nothing to preview or stage).
    cover = await _cover(db_session)
    with_file = _topic(cover.asset_id)
    await repo.add_topic(with_file)
    path = await EditorialCoverImages(db_session).image_file(cover.creator_asset_id)
    assert path is not None
    Path(path).unlink()
    assert await offers.offer(_run(with_file, AutopilotRunState.AWAITING_OWNER)) is None


async def _project(
    session: AsyncSession, cover: SlideCover | None, out: Path
) -> CarouselProject:
    project = CarouselProject(topic="T", audience="Devs", niche="IA")
    project.owner_id = _OWNER
    project.output_dir = str(out)
    project.slide_cover = cover
    return project


@pytest.mark.asyncio
async def test_create_project_stages_or_drops_the_cover(
    db_session: AsyncSession, asset_dirs: Path
) -> None:
    await _seed_owner(db_session)
    creator_id = await _image(db_session)
    asset = await PostgresCreatorAssetRepository(db_session).get_by_id(creator_id)
    assert asset is not None
    cover = SlideCover(
        asset_id=creator_id, kind="ai_image", staged_path=asset.relative_path
    )
    out = asset_dirs / "out-1"
    acl = CarouselAutomationAcl(db_session)
    project_id = await acl.create_project(await _project(db_session, cover, out))
    assert (out / asset.relative_path).is_file()
    repo = PostgresCarouselRepository(session=db_session)
    loaded = await repo.get_project_by_id(UUID(project_id))
    assert loaded is not None and loaded.slide_cover == cover

    gone = SlideCover(
        asset_id=uuid4(), kind="ai_image", staged_path="assets/creators/x.webp"
    )
    dropped_id = await acl.create_project(
        await _project(db_session, gone, asset_dirs / "o2")
    )
    dropped = await repo.get_project_by_id(UUID(dropped_id))
    assert dropped is not None and dropped.slide_cover is None


def _no_lock(
    calls: list[LockedWrite], *, conflict: bool = False
) -> Callable[
    [AsyncSession, LockedWrite, Callable[[], Awaitable[None]]], Awaitable[None]
]:
    async def _write_locked(
        db: AsyncSession, target: LockedWrite, write: Callable[[], Awaitable[None]]
    ) -> None:
        del db
        calls.append(target)
        if conflict:
            raise AutofixConflictError
        await write()

    return _write_locked


@pytest.mark.asyncio
async def test_switch_stages_stores_and_re_renders(
    db_session: AsyncSession, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _seed_owner(db_session)
    creator_id = await _image(db_session)
    asset = await PostgresCreatorAssetRepository(db_session).get_by_id(creator_id)
    assert asset is not None
    out = asset_dirs / "out-switch"
    acl = CarouselAutomationAcl(db_session)
    project_id = await acl.create_project(await _project(db_session, None, out))
    calls: list[LockedWrite] = []
    renders: list[str] = []

    async def _render(_self: object, project: str) -> tuple[str, ...]:
        renders.append(project)
        return ()

    monkeypatch.setattr(slide_cover_switch, "write_locked", _no_lock(calls))
    monkeypatch.setattr(carousel_owner_autofix.RepublishRenderer, "render", _render)
    cover = SlideCover(
        asset_id=creator_id, kind="ai_image", staged_path=asset.relative_path
    )
    switcher = EditorialCoverSwitcher(db_session)

    status = await switcher.switch(
        CoverSwitchCommand(project_id=project_id, expected_version=3, cover=cover)
    )
    assert status is CoverSwitchStatus.SWITCHED
    assert calls == [LockedWrite(project_id=project_id, expected_version=3)]
    assert renders == [project_id]
    assert (out / asset.relative_path).is_file()
    repo = PostgresCarouselRepository(session=db_session)
    loaded = await repo.get_project_by_id(UUID(project_id))
    assert loaded is not None and loaded.slide_cover == cover

    back = await switcher.switch(
        CoverSwitchCommand(project_id=project_id, expected_version=4, cover=None)
    )
    assert back is CoverSwitchStatus.SWITCHED
    loaded = await repo.get_project_by_id(UUID(project_id))
    assert loaded is not None and loaded.slide_cover is None

    gone = SlideCover(asset_id=uuid4(), kind="ai_image", staged_path="a/b.webp")
    missing = await switcher.switch(
        CoverSwitchCommand(project_id=project_id, expected_version=5, cover=gone)
    )
    assert missing is CoverSwitchStatus.MISSING
    unknown = await switcher.switch(
        CoverSwitchCommand(project_id=str(uuid4()), expected_version=5, cover=cover)
    )
    assert unknown is CoverSwitchStatus.MISSING

    monkeypatch.setattr(slide_cover_switch, "write_locked", _no_lock([], conflict=True))
    conflict = await switcher.switch(
        CoverSwitchCommand(project_id=project_id, expected_version=6, cover=None)
    )
    assert conflict is CoverSwitchStatus.CONFLICT
