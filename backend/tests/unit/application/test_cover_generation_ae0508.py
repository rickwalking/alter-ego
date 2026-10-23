"""Grok cover generation: the service, the runner, the picker and the encoder.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature). Fakes for every port; the
photos are generated images.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.application.services.carousel.cover_generation import (
    CoverGenerationConfig,
    CoverGenerationError,
    CoverGenerationForbiddenError,
    CoverGenerationRefusedError,
    CoverGenerationRun,
    CoverGenerationRunner,
    CoverGenerationService,
    CoverRunDeps,
    StartCoverGeneration,
    month_start,
    prompt_digest,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.domain.models.cover_generation import (
    CoverEditJob,
    CoverGeneration,
    CoverGenerationOutcome,
    CoverGenerationStatus,
    ReferencePhoto,
)
from rag_backend.domain.models.slide_cover import CoverAssetError

_OWNER = "00000000-0000-4000-8000-000000000508"
_NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
_PHOTO = uuid4()


def _project(**changes: object) -> CarouselProject:
    project = CarouselProject(topic="T", audience="Devs", niche="IA")
    project.owner_id = _OWNER
    project.content_mode = "pov"
    project.status = CarouselStatus.COMPLETED
    project.phase_status = "awaiting_human"
    for key, value in changes.items():
        setattr(project, key, value)
    return project


def _generation(
    status: CoverGenerationStatus = CoverGenerationStatus.PENDING,
) -> CoverGeneration:
    return CoverGeneration(
        id=uuid4(),
        project_id="p",
        owner_id=_OWNER,
        status=status,
        prompt_sha256="0" * 64,
        photo_count=1,
        model="m",
        cost_usd=0.0,
        created_at=_NOW,
    )


@dataclass
class _Store:
    rows: list[CoverGeneration] = field(default_factory=list)
    month: int = 0
    settled: list[CoverGenerationOutcome] = field(default_factory=list)
    settle_result: bool = True
    stale_cutoffs: list[datetime] = field(default_factory=list)
    commits: int = 0
    locked: list[str] = field(default_factory=list)
    rollbacks: int = 0

    async def lock_owner(self, owner_id: str) -> None:
        self.locked.append(owner_id)

    async def create(self, generation: CoverGeneration) -> None:
        self.rows.append(generation)

    async def for_project(self, project_id: str) -> tuple[CoverGeneration, ...]:
        del project_id
        return tuple(self.rows)

    async def count_owner_since(self, owner_id: str, since: datetime) -> int:
        del owner_id, since
        return self.month

    async def settle(self, outcome: CoverGenerationOutcome) -> bool:
        self.settled.append(outcome)
        return self.settle_result

    async def fail_stale(self, created_before: datetime, at: datetime) -> int:
        del at
        self.stale_cutoffs.append(created_before)
        return 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@dataclass
class _Photos:
    owned: frozenset[UUID] = frozenset({_PHOTO})
    unreadable: bool = False

    async def photo_ids(self, owner_id: str) -> frozenset[UUID]:
        del owner_id
        return self.owned

    async def load(self, asset_ids: tuple[UUID, ...]) -> tuple[ReferencePhoto, ...]:
        if self.unreadable:
            raise CoverAssetError("asset_type_unsupported")
        return tuple(
            ReferencePhoto(content=b"png", mime_type="image/png") for _ in asset_ids
        )


@dataclass
class _Results:
    stored: list[UUID] = field(default_factory=list)
    discarded: list[UUID] = field(default_factory=list)
    invalid: bool = False

    async def store(self, owner_id: str, image: bytes) -> UUID:
        del owner_id, image
        if self.invalid:
            raise CoverAssetError("asset_too_small")
        asset_id = uuid4()
        self.stored.append(asset_id)
        return asset_id

    async def discard(self, asset_id: UUID) -> None:
        self.discarded.append(asset_id)


@dataclass
class _Editor:
    jobs: list[CoverEditJob] = field(default_factory=list)
    error: Exception | None = None

    async def edit_image(self, job: CoverEditJob) -> bytes:
        self.jobs.append(job)
        if self.error is not None:
            raise self.error
        return b"cover"


def _config() -> CoverGenerationConfig:
    return CoverGenerationConfig(
        model="gpt-image-2", cost_usd=0.05, stale_after_seconds=720, now=lambda: _NOW
    )


def _start(**changes: object) -> StartCoverGeneration:
    base = StartCoverGeneration(
        project=_project(),
        user_id=_OWNER,
        photo_ids=(_PHOTO,),
        prompt="no parque",
        confirmed=True,
    )
    return replace(base, **changes)


class TestStart:
    async def test_records_a_pending_row_under_the_owner_lock(self) -> None:
        """Scenario: A confirmed generation sends the photo bytes and stores a private cover."""
        store = _Store()
        service = CoverGenerationService(store, _Photos(), _config())

        run = await service.start(_start())

        assert store.locked == [_OWNER]
        assert store.commits == 1
        assert store.stale_cutoffs == [_NOW - timedelta(seconds=720)]
        generation = run.generation
        assert generation.status is CoverGenerationStatus.PENDING
        assert generation.prompt_sha256 == prompt_digest("no parque")
        assert generation.model == "gpt-image-2"
        assert generation.cost_usd == 0.05
        assert generation.created_at == _NOW
        assert run.photo_ids == (_PHOTO,)
        assert run.prompt == "no parque"

    @pytest.mark.parametrize(
        ("changes", "code"),
        [
            ({"confirmed": False}, "cover_generation_not_confirmed"),
            ({"project": _project(content_mode="news_analysis")}, "cover_pick_not_pov"),
            ({"photo_ids": (uuid4(),)}, "cover_generation_photo_not_allowed"),
        ],
    )
    async def test_refused_requests_record_nothing(
        self, changes: dict[str, object], code: str
    ) -> None:
        """Scenario: Generation needs an explicit confirmation."""
        store = _Store()
        service = CoverGenerationService(store, _Photos(), _config())
        with pytest.raises(CoverGenerationError) as raised:
            await service.start(_start(**changes))
        assert raised.value.code == code
        assert store.rows == []

    @pytest.mark.parametrize("user_id", ["someone-else", ""])
    async def test_only_the_owner(self, user_id: str) -> None:
        """Scenario: Only the carousel's owner can generate."""
        service = CoverGenerationService(_Store(), _Photos(), _config())
        with pytest.raises(CoverGenerationForbiddenError):
            await service.start(_start(user_id=user_id))
        with pytest.raises(CoverGenerationForbiddenError):
            await service.start(_start(project=_project(owner_id=None)))

    @pytest.mark.parametrize(
        ("rows", "month", "code"),
        [
            ([CoverGenerationStatus.PENDING], 0, "cover_generation_in_progress"),
            ([CoverGenerationStatus.SUCCEEDED] * 4, 4, "cover_generation_carousel_cap"),
            ([CoverGenerationStatus.FAILED] * 5, 40, "cover_generation_monthly_cap"),
        ],
    )
    async def test_caps(
        self, rows: list[CoverGenerationStatus], month: int, code: str
    ) -> None:
        """Scenario: The per-carousel cap is four."""
        store = _Store(rows=[_generation(s) for s in rows], month=month)
        service = CoverGenerationService(store, _Photos(), _config())
        with pytest.raises(CoverGenerationRefusedError) as raised:
            await service.start(_start())
        assert raised.value.code == code

    async def test_three_used_and_failed_ones_leave_a_slot(self) -> None:
        """Scenario: A bridge failure leaves no asset and can be retried."""
        rows = [CoverGenerationStatus.SUCCEEDED] * 3 + [
            CoverGenerationStatus.FAILED
        ] * 3
        store = _Store(rows=[_generation(s) for s in rows], month=39)
        run = await CoverGenerationService(store, _Photos(), _config()).start(_start())
        assert run.generation.status is CoverGenerationStatus.PENDING

    async def test_usage_counts_only_live_generations(self) -> None:
        """Scenario: The monthly cap is forty."""
        rows = [CoverGenerationStatus.SUCCEEDED, CoverGenerationStatus.FAILED]
        store = _Store(rows=[_generation(s) for s in rows], month=7)
        usage = await CoverGenerationService(store, _Photos(), _config()).usage(
            _project(), _OWNER
        )
        assert (usage.carousel_used, usage.carousel_cap) == (1, 4)
        assert (usage.month_used, usage.month_cap) == (7, 40)
        assert store.commits == 1


def _runner(
    store: _Store, photos: _Photos, results: _Results, editor: _Editor
) -> CoverGenerationRunner:
    return CoverGenerationRunner(
        CoverRunDeps(
            store=store,
            photos=photos,
            results=results,
            editor=editor,
            render_prompt=lambda text: f"wrapped {text}",
            now=lambda: _NOW,
        )
    )


def _run() -> CoverGenerationRun:
    return CoverGenerationRun(
        generation=_generation(), photo_ids=(_PHOTO,), prompt="no parque"
    )


class TestRunner:
    async def test_success_stores_and_settles(self) -> None:
        """Scenario: A confirmed generation sends the photo bytes and stores a private cover."""
        store, results, editor = _Store(), _Results(), _Editor()
        status = await _runner(store, _Photos(), results, editor).run(_run())
        assert status is CoverGenerationStatus.SUCCEEDED
        assert editor.jobs[0].prompt == "wrapped no parque"
        assert editor.jobs[0].project_id == "p"
        assert store.settled[0].result_asset_id == results.stored[0]
        assert store.settled[0].error_code is None
        assert store.commits == 1

    @pytest.mark.parametrize(
        ("photos", "results", "editor", "code"),
        [
            (
                _Photos(unreadable=True),
                _Results(),
                _Editor(),
                "cover_generation_photo_unreadable",
            ),
            (
                _Photos(),
                _Results(),
                _Editor(error=RuntimeError("x")),
                "cover_generation_bridge_failed",
            ),
            (
                _Photos(),
                _Results(invalid=True),
                _Editor(),
                "cover_generation_invalid_image",
            ),
        ],
    )
    async def test_failures_settle_failed_without_an_asset(
        self, photos: _Photos, results: _Results, editor: _Editor, code: str
    ) -> None:
        """Scenario: A bridge failure leaves no asset and can be retried."""
        store = _Store()
        status = await _runner(store, photos, results, editor).run(_run())
        assert status is CoverGenerationStatus.FAILED
        assert store.settled[0].error_code == code
        assert store.settled[0].result_asset_id is None
        assert results.stored == []
        assert store.commits == 1

    async def test_the_read_transaction_ends_before_the_bridge_wait(self) -> None:
        """Scenario: A confirmed generation sends the photo bytes and stores a private cover."""
        store = _Store()
        seen: list[int] = []

        class _Watching(_Editor):
            async def edit_image(self, job: CoverEditJob) -> bytes:
                seen.append(store.rollbacks)
                return await super().edit_image(job)

        await _runner(store, _Photos(), _Results(), _Watching()).run(_run())

        assert seen == [1]

    async def test_an_unexpected_error_settles_failed(self) -> None:
        """Scenario: A bridge failure leaves no asset and can be retried."""
        store, results = _Store(), _Results()
        editor = _Editor(error=OSError("disk full"))

        status = await _runner(store, _Photos(), results, editor).run(_run())

        assert status is CoverGenerationStatus.FAILED
        assert store.settled[-1].error_code == "cover_generation_failed"
        assert store.rollbacks == 2
        assert results.stored == []

    async def test_a_row_failed_meanwhile_discards_the_image(self) -> None:
        """Scenario: A run lost to a restart is reported as interrupted."""
        store, results = _Store(settle_result=False), _Results()
        status = await _runner(store, _Photos(), results, _Editor()).run(_run())
        assert status is CoverGenerationStatus.FAILED
        assert results.discarded == results.stored


def test_month_start_and_digest() -> None:
    """Scenario: Every call is logged for the budget."""
    assert month_start(_NOW) == datetime(2026, 10, 1, tzinfo=UTC)
    assert len(prompt_digest("x")) == 64
    assert prompt_digest("x") != prompt_digest("y")
    assert _generation(CoverGenerationStatus.FAILED).counts_against_caps is False
    assert _generation(CoverGenerationStatus.SUCCEEDED).counts_against_caps is True
