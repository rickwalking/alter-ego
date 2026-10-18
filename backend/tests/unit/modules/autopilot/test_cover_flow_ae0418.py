"""GrokBot cover through the run: spec, rework, upload, sweep, Telegram (AE-0418).

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs
from uuid import UUID, uuid4

import httpx
import pytest
import respx
from PIL import Image

from rag_backend.domain.models.slide_cover import CoverAssetError, SlideCover
from rag_backend.modules.autopilot.application.cover_sweep import (
    CoverSweepDependencies,
    CoverSweepService,
)
from rag_backend.modules.autopilot.application.cover_upload import (
    CoverOwnerMissingError,
    CoverUploadCommand,
    CoverUploadDependencies,
    CoverUploadService,
)
from rag_backend.modules.autopilot.application.runner import (
    AutopilotRunner,
    RunnerDependencies,
)
from rag_backend.modules.autopilot.application.thesis_prompts import (
    ThesisPromptDependencies,
    ThesisPromptService,
)
from rag_backend.modules.autopilot.constants import GATE_FINAL_REVIEW
from rag_backend.modules.autopilot.cover_constants import (
    COVER_REWORK_PHASE,
    REASON_COVER_MISSING,
)
from rag_backend.modules.autopilot.domain.cover import CoverAsset
from rag_backend.modules.autopilot.domain.cover_offer import CoverOffer
from rag_backend.modules.autopilot.domain.cover_ports import (
    CoverClaim,
    CoverImage,
    CoverSwitchCommand,
    CoverSwitchStatus,
    ExpiredCoverQuery,
    StoredImage,
)
from rag_backend.modules.autopilot.domain.exceptions import TelegramDeliveryError
from rag_backend.modules.autopilot.domain.gate import ProjectSpec
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.notify import (
    ReviewFacts,
    ReviewNotice,
    StatusNotice,
    StatusSendResult,
)
from rag_backend.modules.autopilot.infrastructure.cover_offers import (
    CoverFactsSources,
    CoverReviewFacts,
)
from rag_backend.modules.autopilot.infrastructure.telegram_notifier import (
    TelegramClientConfig,
    TelegramNotifier,
)
from tests.unit.modules.autopilot.project_inputs_fake import FakeProjectInputs
from tests.unit.modules.autopilot.test_autopilot_runner import (
    _OWNER,
    _Editorial,
    _Notices,
    _Recovery,
    _run,
    _Runs,
    _topic,
)
from tests.unit.modules.autopilot.test_pov_thesis_ae0377 import _run as _pov_run
from tests.unit.modules.autopilot.test_pov_thesis_ae0377 import _Store
from tests.unit.modules.autopilot.test_pov_thesis_ae0377 import _topic as _pov_topic

_NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
_S = AutopilotRunState
_COVER = SlideCover(asset_id=uuid4(), kind="ai_image", staged_path="assets/c/x.webp")
_MESSAGE = r"https://api.telegram.org/bot.+/sendMessage$"
_PHOTO = r"https://api.telegram.org/bot.+/sendPhoto$"


class _Clock:
    def now(self) -> datetime:
        return _NOW


@dataclass
class _Offers:
    offer_for: CoverOffer | None = None
    cover: SlideCover | None = _COVER

    async def offer(self, run: AutopilotRun) -> CoverOffer | None:
        if self.offer_for is None:
            return None
        return replace(self.offer_for, chosen=run.cover_chosen)

    async def chosen_cover(self, run: AutopilotRun) -> SlideCover | None:
        return self.cover if run.cover_chosen else None


@dataclass
class _Switcher:
    status: CoverSwitchStatus = CoverSwitchStatus.SWITCHED
    commands: list[CoverSwitchCommand] = field(default_factory=list)

    async def switch(self, command: CoverSwitchCommand) -> CoverSwitchStatus:
        self.commands.append(command)
        return self.status


@dataclass
class _SpecEditorial(_Editorial):
    specs: list[ProjectSpec] = field(default_factory=list)

    async def create_project(self, spec: ProjectSpec) -> str:
        self.specs.append(spec)
        return await super().create_project(spec)


def _runner(
    runs: _Runs,
    editorial: _Editorial,
    covers: _Offers | None,
    switcher: _Switcher | None = None,
) -> tuple[AutopilotRunner, _Notices]:
    notices = _Notices()
    runner = AutopilotRunner(
        RunnerDependencies(
            runs=runs,
            topics=runs,
            editorial=editorial,
            notices=notices,
            recovery=_Recovery(runs=runs),
            owner_user_id=_OWNER,
            inputs=FakeProjectInputs(),
            covers=covers,
            cover_switch=switcher,
        )
    )
    return runner, notices


# --- Default off / chosen at the thesis --------------------------------------------


@pytest.mark.unit
class TestSpecCover:
    # Scenario: The cover is off by default
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("chosen", "wired"), [(False, True), (True, False)])
    async def test_default_slide_one(self, *, chosen: bool, wired: bool) -> None:
        run = replace(_run(_S.QUEUED), cover_chosen=chosen)
        runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
        editorial = _SpecEditorial()
        runner, _notices = _runner(runs, editorial, _Offers() if wired else None)
        await runner.tick()
        assert editorial.specs[0].cover is None

    # Scenario: "Usar capa do Grok" at the thesis switches slide 1 to the cover
    @pytest.mark.asyncio
    async def test_chosen_cover_rides_the_spec(self) -> None:
        run = replace(_run(_S.QUEUED), cover_chosen=True)
        runs = _Runs(run=run, topic=_topic(run.topic_candidate_id))
        editorial = _SpecEditorial()
        runner, _notices = _runner(runs, editorial, _Offers())
        await runner.tick()
        assert editorial.specs[0].cover == _COVER


# --- Switch after content exists ----------------------------------------------------


def _reworking() -> _Runs:
    run = replace(
        _run(_S.REWORKING, project_id="p-1"),
        rework_phase=COVER_REWORK_PHASE,
        cover_chosen=True,
    )
    return _Runs(run=run, topic=_topic(run.topic_candidate_id))


@pytest.mark.unit
class TestCoverRework:
    # Scenario: The Radar IA review offers the cover and swaps slide 1
    @pytest.mark.asyncio
    async def test_switch_then_fresh_review(self) -> None:
        runs = _reworking()
        switcher = _Switcher()
        runner, notices = _runner(
            runs, _Editorial(phase=GATE_FINAL_REVIEW), _Offers(), switcher
        )
        assert await runner.tick() == 1
        assert switcher.commands == [
            CoverSwitchCommand(project_id="p-1", expected_version=4, cover=_COVER)
        ]
        assert runs.run.rework_phase is None
        assert runs.run.state is _S.AWAITING_OWNER
        assert len(notices.events) == 1

    @pytest.mark.asyncio
    async def test_conflict_keeps_the_intent(self) -> None:
        runs = _reworking()
        switcher = _Switcher(status=CoverSwitchStatus.CONFLICT)
        runner, notices = _runner(
            runs, _Editorial(phase=GATE_FINAL_REVIEW), _Offers(), switcher
        )
        assert await runner.tick() == 1
        assert runs.run.rework_phase == COVER_REWORK_PHASE
        assert runs.run.state is _S.REWORKING
        assert notices.events == []

    @pytest.mark.asyncio
    async def test_missing_file_returns_to_the_review(self) -> None:
        runs = _reworking()
        switcher = _Switcher(status=CoverSwitchStatus.MISSING)
        runner, notices = _runner(
            runs, _Editorial(phase=GATE_FINAL_REVIEW), _Offers(), switcher
        )
        await runner.tick()
        assert runs.run.state is _S.AWAITING_OWNER
        assert runs.run.state_reason == REASON_COVER_MISSING
        assert runs.run.rework_phase is None
        assert notices.events == []

    @pytest.mark.asyncio
    async def test_unwired_switch_returns_to_the_review(self) -> None:
        runs = _reworking()
        runner, _notices = _runner(runs, _Editorial(phase=GATE_FINAL_REVIEW), None)
        await runner.tick()
        assert runs.run.state is _S.AWAITING_OWNER
        assert runs.run.rework_phase is None


# --- Upload and sweep services ------------------------------------------------------


@dataclass
class _Covers:
    stored: dict[UUID, CoverAsset] = field(default_factory=dict)
    commits: int = 0
    deleted: list[UUID] = field(default_factory=list)

    async def covers_by_ids(self, ids: tuple[UUID, ...]) -> dict[UUID, CoverAsset]:
        return {key: self.stored[key] for key in ids if key in self.stored}

    async def claim_cover(self, claim: CoverClaim) -> bool:
        del claim
        return True

    async def add_cover(self, cover: CoverAsset) -> None:
        self.stored[cover.asset_id] = cover

    async def expired_covers(self, query: ExpiredCoverQuery) -> tuple[CoverAsset, ...]:
        old = [c for c in self.stored.values() if c.created_at < query.before]
        return tuple(old[: query.limit])

    async def delete_covers(self, ids: tuple[UUID, ...]) -> None:
        self.deleted.extend(ids)

    async def commit(self) -> None:
        self.commits += 1


@dataclass
class _Images:
    reject: str | None = None
    images: list[CoverImage] = field(default_factory=list)
    deleted: list[UUID] = field(default_factory=list)

    async def store_image(self, image: CoverImage) -> StoredImage:
        if self.reject is not None:
            raise CoverAssetError(self.reject)
        self.images.append(image)
        return StoredImage(creator_asset_id=uuid4(), width=800, height=400)

    async def image_file(self, creator_asset_id: UUID) -> str | None:
        del creator_asset_id
        return None

    async def delete_images(self, creator_asset_ids: tuple[UUID, ...]) -> int:
        self.deleted.extend(creator_asset_ids)
        return len(creator_asset_ids)


def _upload(covers: _Covers, images: _Images, owner: str = "u-1") -> CoverUploadService:
    return CoverUploadService(
        CoverUploadDependencies(
            covers=covers, images=images, clock=_Clock(), owner_user_id=owner
        )
    )


@pytest.mark.unit
class TestUploadService:
    @pytest.mark.asyncio
    async def test_screenshot_keeps_the_canonical_source(self) -> None:
        covers, images = _Covers(), _Images()
        result = await _upload(covers, images).upload(
            CoverUploadCommand(
                content=b"png", kind="screenshot", source_url="https://Example.com/a/"
            )
        )
        stored = covers.stored[result.asset_id]
        assert (result.kind, result.width, result.height) == ("screenshot", 800, 400)
        assert stored.source_url == "https://example.com/a"
        assert stored.created_at == _NOW
        assert images.images[0].owner_id == "u-1"
        assert covers.commits == 1

    @pytest.mark.asyncio
    async def test_ai_image_drops_a_source(self) -> None:
        covers = _Covers()
        result = await _upload(covers, _Images()).upload(
            CoverUploadCommand(
                content=b"png", kind="ai_image", source_url="https://a.b"
            )
        )
        assert covers.stored[result.asset_id].source_url is None

    @pytest.mark.asyncio
    async def test_form_and_image_rejections(self) -> None:
        covers = _Covers()
        with pytest.raises(CoverAssetError) as bad_kind:
            await _upload(covers, _Images()).upload(
                CoverUploadCommand(content=b"x", kind=None, source_url=None)
            )
        assert bad_kind.value.code == "asset_kind_invalid"
        with pytest.raises(CoverAssetError) as small:
            await _upload(covers, _Images(reject="asset_too_small")).upload(
                CoverUploadCommand(content=b"x", kind="ai_image", source_url=None)
            )
        assert small.value.code == "asset_too_small"
        assert covers.stored == {}
        assert covers.commits == 0

    @pytest.mark.asyncio
    async def test_owner_is_required(self) -> None:
        with pytest.raises(CoverOwnerMissingError):
            await _upload(_Covers(), _Images(), owner="  ").upload(
                CoverUploadCommand(content=b"x", kind="ai_image", source_url=None)
            )


def _stored(age_hours: float) -> CoverAsset:
    return CoverAsset(
        asset_id=uuid4(),
        creator_asset_id=uuid4(),
        kind="ai_image",
        source_url=None,
        width=1080,
        height=1350,
        created_at=_NOW - timedelta(hours=age_hours),
    )


@pytest.mark.unit
class TestSweep:
    # Scenario: Unused covers older than 6 hours are deleted
    @pytest.mark.asyncio
    async def test_deletes_only_expired_covers(self) -> None:
        old, fresh = _stored(7), _stored(1)
        covers = _Covers(stored={old.asset_id: old, fresh.asset_id: fresh})
        images = _Images()
        sweep = CoverSweepService(
            CoverSweepDependencies(covers=covers, images=images, clock=_Clock())
        )
        assert await sweep.tick() == 1
        assert covers.deleted == [old.asset_id]
        assert images.deleted == [old.creator_asset_id]
        assert covers.commits == 1

    @pytest.mark.asyncio
    async def test_nothing_to_sweep(self) -> None:
        covers = _Covers(stored={})
        sweep = CoverSweepService(
            CoverSweepDependencies(covers=covers, images=_Images(), clock=_Clock())
        )
        assert await sweep.tick() == 0
        assert covers.commits == 0


# --- Thesis prompt preview ------------------------------------------------------------


_OFFER = CoverOffer(kind="ai_image", credit="", chosen=False, pov=True, photo_path="/c")


@dataclass
class _PhotoDownStore(_Store):
    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        if notice.photo_path:
            raise TelegramDeliveryError("photo down")
        return await super().send_status(notice)


def _prompts(store: _Store, offers: _Offers | None) -> ThesisPromptService:
    return ThesisPromptService(
        ThesisPromptDependencies(
            runs=store,
            topics=store,
            notices=store,
            notifier=store,
            chat_id="42",
            configured=True,
            covers=offers,
        )
    )


@pytest.mark.unit
class TestThesisPreview:
    # Scenario: The POV thesis message offers the cover
    @pytest.mark.asyncio
    async def test_photo_then_prompt_with_the_toggle_once(self) -> None:
        store = _Store(run=_pov_run(_S.AWAITING_THESIS), topic=_pov_topic())
        assert await _prompts(store, _Offers(offer_for=_OFFER)).tick() == 1
        assert await _prompts(store, _Offers(offer_for=_OFFER)).tick() == 0
        photo, prompt = store.sent
        assert photo.photo_path == "/c"
        assert photo.keyboard is None
        assert prompt.keyboard is not None
        assert prompt.keyboard.rows[-1][0].text == "🖼️ Usar capa do Grok"

    @pytest.mark.asyncio
    async def test_failed_photo_still_sends_the_prompt(self) -> None:
        store = _PhotoDownStore(run=_pov_run(_S.AWAITING_THESIS), topic=_pov_topic())
        assert await _prompts(store, _Offers(offer_for=_OFFER)).tick() == 1
        assert [n.photo_path for n in store.sent] == [None]

    @pytest.mark.asyncio
    async def test_no_offer_no_photo(self) -> None:
        store = _Store(run=_pov_run(_S.AWAITING_THESIS), topic=_pov_topic())
        assert await _prompts(store, _Offers()).tick() == 1
        assert len(store.sent) == 1
        assert store.sent[0].keyboard is not None
        assert len(store.sent[0].keyboard.rows) == 1


# --- Review facts and the Telegram adapter -------------------------------------------


@dataclass
class _Facts:
    facts: ReviewFacts | None

    async def load(self, project_id: str) -> ReviewFacts | None:
        del project_id
        return self.facts


@dataclass
class _ByCarousel:
    run: AutopilotRun | None

    async def find_by_carousel(self, project_id: str) -> AutopilotRun | None:
        del project_id
        return self.run


def _decorated(inner: ReviewFacts | None, run: AutopilotRun | None) -> CoverReviewFacts:
    return CoverReviewFacts(
        _Facts(facts=inner),
        CoverFactsSources(runs=_ByCarousel(run=run), offers=_Offers(offer_for=_OFFER)),
    )


@pytest.mark.unit
class TestReviewFacts:
    @pytest.mark.asyncio
    async def test_adds_the_offer(self) -> None:
        base = ReviewFacts(title="t", caption="c", slide_paths=())
        loaded = await _decorated(base, _run(_S.AWAITING_OWNER)).load("p")
        assert loaded is not None
        assert loaded.cover == _OFFER

    @pytest.mark.asyncio
    async def test_passes_through_without_a_run_or_facts(self) -> None:
        base = ReviewFacts(title="t", caption="c", slide_paths=())
        assert await _decorated(base, None).load("p") == base
        assert await _decorated(None, _run(_S.AWAITING_OWNER)).load("p") is None


class _NoSleep:
    async def sleep(self, seconds: float) -> None:
        del seconds


def _webp(tmp_path: Path) -> str:
    path = tmp_path / "cover.webp"
    buffer = BytesIO()
    Image.new("RGB", (20, 25), (1, 2, 3)).save(buffer, format="WEBP")
    path.write_bytes(buffer.getvalue())
    return str(path)


def _ok(message_id: int) -> httpx.Response:
    return httpx.Response(200, json={"ok": True, "result": {"message_id": message_id}})


def _review(
    tmp_path: Path, cover: CoverOffer | None, prior: tuple[int, ...] = ()
) -> ReviewNotice:
    slide = tmp_path / "slide_1.jpg"
    slide.write_bytes(b"\xff\xd8\xff" + b"x" * 8)
    return ReviewNotice(
        chat_id="42",
        run_id=UUID("22222222-2222-4222-8222-222222222222"),
        title="T",
        persona_score=80.0,
        sources_count=2,
        caption="caption",
        slide_paths=(str(slide),),
        prior_album_ids=prior,
        cover=cover,
    )


def _notifier() -> TelegramNotifier:
    return TelegramNotifier(TelegramClientConfig(token="t", sleeper=_NoSleep()))


@pytest.mark.unit
class TestTelegramCover:
    @pytest.mark.asyncio
    async def test_review_sends_the_cover_preview_and_the_toggle(
        self, tmp_path: Path
    ) -> None:
        cover = replace(_OFFER, photo_path=_webp(tmp_path), pov=False)
        with respx.mock(assert_all_called=True) as router:
            photo = router.post(url__regex=_PHOTO).mock(side_effect=[_ok(1), _ok(2)])
            message = router.post(url__regex=_MESSAGE).mock(return_value=_ok(3))
            result = await _notifier().send_review(_review(tmp_path, cover))
        assert result.album_ids == (1,)
        assert len(photo.calls) == 2
        assert b"image/jpeg" in photo.calls[1].request.content
        form = parse_qs(message.calls[0].request.content.decode())
        rows = json.loads(form["reply_markup"][0])["inline_keyboard"]
        assert rows[-1][0]["text"] == "🖼️ Usar capa do Grok"

    @pytest.mark.asyncio
    async def test_chosen_or_resent_reviews_skip_the_preview(
        self, tmp_path: Path
    ) -> None:
        chosen = replace(_OFFER, photo_path=_webp(tmp_path), chosen=True, pov=False)
        with respx.mock(assert_all_called=True) as router:
            photo = router.post(url__regex=_PHOTO).mock(return_value=_ok(1))
            message = router.post(url__regex=_MESSAGE).mock(return_value=_ok(3))
            await _notifier().send_review(_review(tmp_path, chosen))
            await _notifier().send_review(_review(tmp_path, _OFFER, prior=(1,)))
        assert len(photo.calls) == 1
        form = parse_qs(message.calls[0].request.content.decode())
        rows = json.loads(form["reply_markup"][0])["inline_keyboard"]
        assert rows[-1][0]["text"] == "↩️ Usar capa padrão"

    @pytest.mark.asyncio
    async def test_failed_preview_does_not_block_the_review(
        self, tmp_path: Path
    ) -> None:
        broken = replace(_OFFER, photo_path=str(tmp_path / "gone.webp"))
        with respx.mock(assert_all_called=True) as router:
            router.post(url__regex=_PHOTO).mock(return_value=_ok(1))
            router.post(url__regex=_MESSAGE).mock(return_value=_ok(3))
            result = await _notifier().send_review(_review(tmp_path, broken))
        assert result.keyboard_id == 3

    @pytest.mark.asyncio
    async def test_status_photo_carries_caption_and_keyboard(
        self, tmp_path: Path
    ) -> None:
        notice = StatusNotice(
            chat_id="42",
            run_id=uuid4(),
            text="Capa",
            keyboard=None,
            photo_path=_webp(tmp_path),
        )
        with respx.mock(assert_all_called=True) as router:
            photo = router.post(url__regex=_PHOTO).mock(return_value=_ok(5))
            result = await _notifier().send_status(notice)
        assert result.message_id == 5
        body = photo.calls[0].request.content
        assert b"Capa" in body
        assert b"cover.jpg" in body
