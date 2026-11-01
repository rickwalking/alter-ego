"""Autopilot cover auto-selection: the selector's rules over a fake store.

Gherkin: tests/features/autopilot_cover_autoselect_ae0590.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import UUID, uuid4

import pytest
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverPolling,
    AutoCoverSelection,
    AutoCoverSelector,
    AutoCoverWrite,
    CoverBaseline,
    ProjectAtVersion,
    choice_refusal,
    cover_baseline,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
)
from rag_backend.domain.constants.cover_autoselect import (
    LOG_COVER_AUTO_SELECT,
    OUTCOME_AUTO_SELECT_ALREADY,
    OUTCOME_AUTO_SELECT_SELECTED,
    REASON_AUTO_SELECT_ASSET_GONE,
    REASON_AUTO_SELECT_COMPLETED,
    REASON_AUTO_SELECT_CONFLICT,
    REASON_AUTO_SELECT_FAILED,
    REASON_AUTO_SELECT_MANUAL_CHOICE,
    REASON_AUTO_SELECT_NO_PROJECT,
    REASON_AUTO_SELECT_NO_RESULT,
    REASON_AUTO_SELECT_OWNER_COVER,
    REASON_AUTO_SELECT_TIMED_OUT,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.domain.models.slide_cover import SlideCover

_HOOK = uuid4()
_ASSET = uuid4()
_GENERATION = uuid4()


def _project(**changes: object) -> CarouselProject:
    project = CarouselProject(topic="Agentes", audience="Devs", niche="IA")
    project.content_mode = "pov"
    project.hook_asset_id = _HOOK
    project.status = CarouselStatus.DRAFTING
    project.current_phase = "content"
    project.phase_status = "awaiting_human"
    for name, value in changes.items():
        setattr(project, name, value)
    return project


def _cover(asset_id: UUID) -> SlideCover:
    return SlideCover(asset_id=asset_id, kind="ai_image", staged_path="c.webp")


_BASELINE = CoverBaseline(slide_cover_asset_id=None, hook_asset_id=_HOOK)


def _selection(baseline: CoverBaseline = _BASELINE) -> AutoCoverSelection:
    return AutoCoverSelection(
        project_id="p-1", generation_id=_GENERATION, baseline=baseline
    )


@dataclass
class _Store:
    """Answers the reads in order (the last one repeats) and records writes."""

    reads: list[CarouselProject | None]
    asset: UUID | None = _ASSET
    status: str = AUTOFIX_STATUS_FIXED
    writes: list[AutoCoverWrite] = field(default_factory=list)
    loads: int = 0

    async def result_asset(self, generation_id: UUID) -> UUID | None:
        assert generation_id == _GENERATION
        return self.asset

    async def load(self, project_id: str) -> ProjectAtVersion | None:
        index = min(self.loads, len(self.reads) - 1)
        self.loads += 1
        project = self.reads[index]
        if project is None:
            return None
        return ProjectAtVersion(project=project, lock_version=7 + index)

    async def write(self, command: AutoCoverWrite) -> str:
        self.writes.append(command)
        return self.status


@dataclass
class _Sleeps:
    calls: list[float] = field(default_factory=list)

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _selector(store: _Store, sleeps: _Sleeps | None = None) -> AutoCoverSelector:
    polling = AutoCoverPolling(
        interval_seconds=5.0, max_wait_seconds=15.0, sleep=sleeps or _Sleeps()
    )
    return AutoCoverSelector(store, polling)


@pytest.mark.unit
class TestAutoCoverSelector:
    # Scenario: A succeeded autopilot cover becomes slide 1's cover
    @pytest.mark.asyncio
    async def test_selects_at_the_version_read(self) -> None:
        store = _Store(reads=[_project()])

        with capture_logs() as logs:
            outcome = await _selector(store).select(_selection())

        assert outcome == OUTCOME_AUTO_SELECT_SELECTED
        assert store.writes == [
            AutoCoverWrite(
                project_id="p-1",
                asset_id=_ASSET,
                expected_version=7,
                baseline=_BASELINE,
            )
        ]
        assert logs[-1]["event"] == LOG_COVER_AUTO_SELECT
        assert logs[-1]["outcome"] == OUTCOME_AUTO_SELECT_SELECTED

    # Scenario: The selection waits for the workflow to pause at a gate
    @pytest.mark.asyncio
    async def test_waits_until_paused(self) -> None:
        running = _project(phase_status="in_progress")
        store = _Store(reads=[running, running, _project()])
        sleeps = _Sleeps()

        outcome = await _selector(store, sleeps).select(_selection())

        assert outcome == OUTCOME_AUTO_SELECT_SELECTED
        assert sleeps.calls == [5.0, 5.0]
        assert store.writes[0].expected_version == 9

    # Scenario: The wait gives up after its deadline
    @pytest.mark.asyncio
    async def test_times_out_while_running(self) -> None:
        store = _Store(reads=[_project(phase_status="in_progress")])
        sleeps = _Sleeps()

        with capture_logs() as logs:
            outcome = await _selector(store, sleeps).select(_selection())

        assert outcome == REASON_AUTO_SELECT_TIMED_OUT
        assert sleeps.calls == [5.0, 5.0, 5.0]
        assert store.writes == []
        assert logs[-1]["reason"] == REASON_AUTO_SELECT_TIMED_OUT

    # Scenario: A cover the owner chose before the job is kept
    @pytest.mark.asyncio
    async def test_owner_cover_before_the_job_is_kept(self) -> None:
        owner_cover = uuid4()
        store = _Store(reads=[_project(slide_cover=_cover(owner_cover))])
        baseline = replace(_BASELINE, slide_cover_asset_id=owner_cover)

        outcome = await _selector(store).select(_selection(baseline))

        assert outcome == REASON_AUTO_SELECT_OWNER_COVER
        assert store.writes == []

    # Scenario: A manual choice made while the job ran is kept
    @pytest.mark.asyncio
    async def test_rebound_photo_is_kept(self) -> None:
        store = _Store(reads=[_project(hook_asset_id=uuid4())])

        outcome = await _selector(store).select(_selection())

        assert outcome == REASON_AUTO_SELECT_MANUAL_CHOICE
        assert store.writes == []

    # Scenario: A manual choice made while the job ran is kept
    @pytest.mark.asyncio
    async def test_cover_set_while_running_is_kept(self) -> None:
        store = _Store(reads=[_project(slide_cover=_cover(uuid4()))])

        outcome = await _selector(store).select(_selection())

        assert outcome == REASON_AUTO_SELECT_MANUAL_CHOICE
        assert store.writes == []

    # Scenario: Selecting the same cover twice changes nothing
    @pytest.mark.asyncio
    async def test_already_selected_is_a_no_op(self) -> None:
        store = _Store(reads=[_project(slide_cover=_cover(_ASSET))])

        with capture_logs() as logs:
            outcome = await _selector(store).select(_selection())

        assert outcome == OUTCOME_AUTO_SELECT_ALREADY
        assert store.writes == []
        assert logs[-1]["outcome"] == OUTCOME_AUTO_SELECT_ALREADY

    # Scenario: A carousel already at the owner's review keeps its cover
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("changes", "reason"),
        [
            ({"status": CarouselStatus.COMPLETED}, REASON_AUTO_SELECT_COMPLETED),
            ({"current_phase": "final_review"}, REASON_AUTO_SELECT_COMPLETED),
            ({"status": CarouselStatus.FAILED}, REASON_AUTO_SELECT_FAILED),
        ],
    )
    async def test_review_or_failed_carousel_is_skipped(
        self, changes: dict[str, object], reason: str
    ) -> None:
        store = _Store(reads=[_project(phase_status="in_progress", **changes)])
        sleeps = _Sleeps()

        outcome = await _selector(store, sleeps).select(_selection())

        assert outcome == reason
        assert store.writes == []
        assert sleeps.calls == []

    # Scenario: A lock-version conflict is skipped and logged, never retried
    @pytest.mark.asyncio
    async def test_conflict_is_skipped_once(self) -> None:
        store = _Store(reads=[_project()], status=AUTOFIX_STATUS_CONFLICT)

        with capture_logs() as logs:
            outcome = await _selector(store).select(_selection())

        assert outcome == REASON_AUTO_SELECT_CONFLICT
        assert len(store.writes) == 1
        assert logs[-1]["reason"] == REASON_AUTO_SELECT_CONFLICT

    # Scenario: A generated cover whose file is gone is skipped
    @pytest.mark.asyncio
    async def test_write_refusal_passes_through(self) -> None:
        store = _Store(reads=[_project()], status=REASON_AUTO_SELECT_ASSET_GONE)

        outcome = await _selector(store).select(_selection())

        assert outcome == REASON_AUTO_SELECT_ASSET_GONE

    # Scenario: A failed generation leaves slide 1 alone
    @pytest.mark.asyncio
    async def test_no_result_never_reads_or_writes(self) -> None:
        store = _Store(reads=[_project()], asset=None)

        outcome = await _selector(store).select(_selection())

        assert outcome == REASON_AUTO_SELECT_NO_RESULT
        assert store.loads == 0
        assert store.writes == []

    @pytest.mark.asyncio
    async def test_gone_project_is_skipped(self) -> None:
        store = _Store(reads=[None])

        outcome = await _selector(store).select(_selection())

        assert outcome == REASON_AUTO_SELECT_NO_PROJECT

    def test_default_polling(self) -> None:
        selector = AutoCoverSelector(_Store(reads=[None]))

        assert selector._polling.interval_seconds == 5.0
        assert selector._polling.max_wait_seconds == 45 * 60.0


@pytest.mark.unit
class TestChoiceRules:
    def test_baseline_of_default_slide_one(self) -> None:
        assert cover_baseline(_project()) == _BASELINE

    def test_baseline_records_a_chosen_cover(self) -> None:
        owner_cover = uuid4()

        found = cover_baseline(_project(slide_cover=_cover(owner_cover)))

        assert found.slide_cover_asset_id == owner_cover

    def test_unchanged_default_is_allowed(self) -> None:
        assert choice_refusal(_project(), _BASELINE, _ASSET) is None
