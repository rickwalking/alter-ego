"""The review switch of a website cover, and the guard, over fakes.

Gherkin: tests/features/website_cover_review_switch_ae0594.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
)
from rag_backend.application.services.carousel.cover_pick import (
    CoverPickCommand,
    CoverPickDeps,
    CoverPickError,
    CoverPickService,
)
from rag_backend.application.services.carousel.cover_review_switch import (
    NoReviewHold,
    ReviewSwitch,
    ReviewSwitchOutcome,
    switch_in_review,
)
from rag_backend.application.services.carousel.cover_switch_guard import (
    cover_switch_refusal,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
)
from rag_backend.domain.constants.cover_autoselect import (
    LOG_COVER_AUTO_SELECT,
    OUTCOME_AUTO_SELECT_ALREADY,
    OUTCOME_AUTO_SELECT_SELECTED,
    REASON_AUTO_SELECT_COMPLETED,
    REASON_AUTO_SELECT_CONFLICT,
    REASON_AUTO_SELECT_FAILED,
    REASON_AUTO_SELECT_MANUAL_CHOICE,
)
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
    LOG_COVER_REVIEW_RENDER_FAILED,
    REASON_AUTO_SELECT_APPROVED,
    REASON_AUTO_SELECT_NOT_IN_REVIEW,
    REASON_AUTO_SELECT_PUBLISHED,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.domain.models.slide_cover import SlideCover
from tests.unit.application.test_cover_pick_ae0445 import (
    _Library,
    _Offers,
    _photo,
    _Switcher,
)

_HOOK = uuid4()
_ASSET = uuid4()
_GENERATION = uuid4()
_RUN = uuid4()
_BASELINE = CoverBaseline(slide_cover_asset_id=None, hook_asset_id=_HOOK)
_APPROVED = "approved_for_publish"


def _project(**changes: object) -> CarouselProject:
    project = CarouselProject(topic="Agentes", audience="Devs", niche="IA")
    project.content_mode = "pov"
    project.hook_asset_id = _HOOK
    project.status = CarouselStatus.COMPLETED
    project.current_phase = "final_review"
    project.phase_status = "awaiting_human"
    for name, value in changes.items():
        setattr(project, name, value)
    return project


@dataclass
class _Reads:
    """The selector's fresh reads: one project and its approval."""

    project: CarouselProject
    workflow_status: str = "draft"
    writes: list[AutoCoverWrite] = field(default_factory=list)

    async def result_asset(self, generation_id: UUID) -> UUID | None:
        assert generation_id == _GENERATION
        return _ASSET

    async def load(self, project_id: str) -> ProjectAtVersion | None:
        del project_id
        return ProjectAtVersion(
            project=self.project, lock_version=7, workflow_status=self.workflow_status
        )

    async def write(self, command: AutoCoverWrite) -> str:
        self.writes.append(command)
        return AUTOFIX_STATUS_FIXED


@dataclass
class _ReviewStore:
    outcome: ReviewSwitchOutcome = field(
        default_factory=lambda: ReviewSwitchOutcome(status=AUTOFIX_STATUS_FIXED)
    )
    error: Exception | None = None
    writes: list[AutoCoverWrite] = field(default_factory=list)

    async def switch_in_review(self, command: AutoCoverWrite) -> ReviewSwitchOutcome:
        self.writes.append(command)
        if self.error is not None:
            raise self.error
        return self.outcome


@dataclass
class _Hold:
    run_id: UUID | None = _RUN
    held: list[str] = field(default_factory=list)
    released: list[tuple[UUID, bool]] = field(default_factory=list)

    async def hold(self, project_id: str) -> UUID | None:
        self.held.append(project_id)
        return self.run_id

    async def release(self, run_id: UUID, *, changed: bool) -> None:
        self.released.append((run_id, changed))


async def _no_sleep(seconds: float) -> None:
    del seconds


def _select(
    reads: _Reads, review: ReviewSwitch | None
) -> tuple[AutoCoverSelector, AutoCoverSelection]:
    selection = AutoCoverSelection(
        project_id="p-1", generation_id=_GENERATION, baseline=_BASELINE, review=review
    )
    polling = AutoCoverPolling(
        interval_seconds=1.0, max_wait_seconds=1.0, sleep=_no_sleep
    )
    return AutoCoverSelector(reads, polling), selection


def _reasons(logs: list[dict[str, object]]) -> list[object]:
    return [e.get("reason") for e in logs if e["event"] == LOG_COVER_AUTO_SELECT]


@pytest.mark.unit
class TestReviewSwitch:
    # Scenario: A website cover switches a completed carousel in final review
    # Scenario: The Telegram review is held while slide 1 changes
    @pytest.mark.asyncio
    async def test_switches_a_completed_carousel_in_review(self) -> None:
        store, hold = _ReviewStore(), _Hold()
        selector, selection = _select(
            _Reads(_project()), ReviewSwitch(store=store, hold=hold)
        )

        outcome = await selector.select(selection)

        assert outcome == OUTCOME_AUTO_SELECT_SELECTED
        assert store.writes == [
            AutoCoverWrite(
                project_id="p-1",
                asset_id=_ASSET,
                expected_version=7,
                baseline=_BASELINE,
            )
        ]
        assert hold.held == ["p-1"]
        assert hold.released == [(_RUN, True)]

    # Scenario: A website cover switches a completed carousel in final review
    @pytest.mark.asyncio
    async def test_a_failed_render_is_logged_and_still_selected(self) -> None:
        store = _ReviewStore(
            outcome=ReviewSwitchOutcome(
                status=AUTOFIX_STATUS_FIXED, render_errors=("x",)
            )
        )
        selector, selection = _select(
            _Reads(_project()), ReviewSwitch(store=store, hold=NoReviewHold())
        )

        with capture_logs() as logs:
            outcome = await selector.select(selection)

        assert outcome == OUTCOME_AUTO_SELECT_SELECTED
        failed = [e for e in logs if e["event"] == LOG_COVER_REVIEW_RENDER_FAILED]
        assert failed[0]["errors"] == ["x"]
        assert failed[0]["log_level"] == "warning"

    # Scenario: A lock conflict on a completed carousel is skipped and logged
    @pytest.mark.asyncio
    async def test_a_conflict_is_skipped_and_the_review_handed_back(self) -> None:
        store = _ReviewStore(
            outcome=ReviewSwitchOutcome(status=AUTOFIX_STATUS_CONFLICT)
        )
        hold = _Hold()
        selector, selection = _select(
            _Reads(_project()), ReviewSwitch(store=store, hold=hold)
        )

        with capture_logs() as logs:
            outcome = await selector.select(selection)

        assert outcome == REASON_AUTO_SELECT_CONFLICT
        assert _reasons(logs) == [REASON_AUTO_SELECT_CONFLICT]
        assert hold.released == [(_RUN, False)]

    # Scenario: The Telegram review is held while slide 1 changes
    @pytest.mark.asyncio
    async def test_a_store_crash_releases_as_changed(self) -> None:
        store, hold = _ReviewStore(error=RuntimeError("boom")), _Hold()
        selector, selection = _select(
            _Reads(_project()), ReviewSwitch(store=store, hold=hold)
        )

        with pytest.raises(RuntimeError, match="boom"):
            await selector.select(selection)

        assert hold.released == [(_RUN, True)]

    # Scenario: A website cover switches a completed carousel in final review
    @pytest.mark.asyncio
    async def test_no_held_run_is_never_released(self) -> None:
        store, hold = _ReviewStore(), _Hold(run_id=None)
        selector, selection = _select(
            _Reads(_project()), ReviewSwitch(store=store, hold=hold)
        )

        assert await selector.select(selection) == OUTCOME_AUTO_SELECT_SELECTED
        assert hold.released == []

    # Scenario: A website cover on an approved or scheduled carousel stays a picker option
    # Scenario: A website cover on a published carousel stays a picker option
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("reads", "reason"),
        [
            (
                _Reads(_project(), workflow_status=_APPROVED),
                REASON_AUTO_SELECT_APPROVED,
            ),
            (_Reads(_project(is_public=True)), REASON_AUTO_SELECT_PUBLISHED),
            (
                _Reads(_project(current_phase="images")),
                REASON_AUTO_SELECT_NOT_IN_REVIEW,
            ),
            (
                _Reads(_project(phase_status="approved")),
                REASON_AUTO_SELECT_NOT_IN_REVIEW,
            ),
            (_Reads(_project(phase_status="rejected")), REASON_AUTO_SELECT_FAILED),
        ],
    )
    async def test_refusals_never_hold_or_write(
        self, reads: _Reads, reason: str
    ) -> None:
        store, hold = _ReviewStore(), _Hold()
        selector, selection = _select(reads, ReviewSwitch(store=store, hold=hold))

        with capture_logs() as logs:
            outcome = await selector.select(selection)

        assert outcome == reason
        assert _reasons(logs) == [reason]
        assert store.writes == []
        assert hold.held == []

    # Scenario: A cover the owner chose while the job ran wins on a completed carousel
    @pytest.mark.asyncio
    async def test_a_change_since_the_baseline_wins(self) -> None:
        store, hold = _ReviewStore(), _Hold()
        moved = _project(hook_asset_id=uuid4())
        selector, selection = _select(
            _Reads(moved), ReviewSwitch(store=store, hold=hold)
        )

        assert await selector.select(selection) == REASON_AUTO_SELECT_MANUAL_CHOICE
        assert store.writes == []
        assert hold.held == []

    # Scenario: A website cover switches a completed carousel in final review
    @pytest.mark.asyncio
    async def test_a_cover_chosen_before_the_job_does_not_block(self) -> None:
        chosen = SlideCover(asset_id=uuid4(), kind="ai_image", staged_path="c.webp")
        baseline = CoverBaseline(
            slide_cover_asset_id=chosen.asset_id, hook_asset_id=_HOOK
        )
        store = _ReviewStore()
        selection = AutoCoverSelection(
            project_id="p-1",
            generation_id=_GENERATION,
            baseline=baseline,
            review=ReviewSwitch(store=store, hold=NoReviewHold()),
        )
        selector = AutoCoverSelector(_Reads(_project(slide_cover=chosen)))

        assert await selector.select(selection) == OUTCOME_AUTO_SELECT_SELECTED
        assert len(store.writes) == 1

    # Scenario: Replaying a website cover success changes nothing
    @pytest.mark.asyncio
    async def test_a_replay_is_already_selected(self) -> None:
        already = SlideCover(asset_id=_ASSET, kind="ai_image", staged_path="c.webp")
        store, hold = _ReviewStore(), _Hold()
        selector, selection = _select(
            _Reads(_project(slide_cover=already)), ReviewSwitch(store=store, hold=hold)
        )

        assert await selector.select(selection) == OUTCOME_AUTO_SELECT_ALREADY
        assert store.writes == []
        assert hold.held == []

    # Scenario: An autopilot cover on a completed carousel is unchanged
    @pytest.mark.asyncio
    async def test_without_a_review_switch_a_completed_carousel_is_skipped(
        self,
    ) -> None:
        reads = _Reads(_project())
        selector, selection = _select(reads, None)

        assert await selector.select(selection) == REASON_AUTO_SELECT_COMPLETED
        assert reads.writes == []

    # Scenario: A website cover switches a completed carousel in final review
    @pytest.mark.asyncio
    async def test_a_carousel_before_its_review_keeps_the_gate_write(self) -> None:
        reads = _Reads(
            _project(status=CarouselStatus.DRAFTING, current_phase="content")
        )
        store = _ReviewStore()
        selector, selection = _select(
            reads, ReviewSwitch(store=store, hold=NoReviewHold())
        )

        assert await selector.select(selection) == OUTCOME_AUTO_SELECT_SELECTED
        assert len(reads.writes) == 1
        assert store.writes == []

    # Scenario: A website cover switches a completed carousel in final review
    @pytest.mark.asyncio
    async def test_switch_without_review_deps_is_refused(self) -> None:
        selection = AutoCoverSelection(
            project_id="p-1", generation_id=_GENERATION, baseline=_BASELINE
        )
        found = ProjectAtVersion(project=_project(), lock_version=7)

        result = await switch_in_review(selection, (found, _ASSET))

        assert result == REASON_AUTO_SELECT_NOT_IN_REVIEW

    # Scenario: A website cover switches a completed carousel in final review
    @pytest.mark.asyncio
    async def test_no_review_hold_holds_nothing(self) -> None:
        hold = NoReviewHold()

        assert await hold.hold("p-1") is None
        await hold.release(_RUN, changed=True)


@pytest.mark.unit
class TestGuard:
    # Scenario: The picker refuses an approved carousel
    # Scenario: The picker refuses a published carousel
    def test_refusal_reasons(self) -> None:
        assert cover_switch_refusal(_project(), "draft") is None
        assert cover_switch_refusal(_project(), "") is None
        assert (
            cover_switch_refusal(_project(), _APPROVED) == REASON_AUTO_SELECT_APPROVED
        )
        published = _project(is_public=True)
        assert cover_switch_refusal(published, "draft") == REASON_AUTO_SELECT_PUBLISHED

    # Scenario: The picker refuses an approved carousel
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("status", "public"), [(_APPROVED, False), ("draft", True), (_APPROVED, True)]
    )
    async def test_picker_refuses_before_switching(
        self, status: str, public: bool
    ) -> None:
        @dataclass
        class _Review:
            async def workflow_status(self, project_id: str) -> str:
                del project_id
                return status

        a, b = _photo("a"), _photo("b")
        switcher = _Switcher()
        service = CoverPickService(
            CoverPickDeps(
                library=_Library((a, b)),
                offers=_Offers(),
                switcher=switcher,
                review=_Review(),
            )
        )
        project = _project(owner_id="owner-1", hook_asset_id=a.id, is_public=public)

        with pytest.raises(CoverPickError) as refused:
            await service.pick(
                CoverPickCommand(project=project, asset_id=b.id, expected_version=7)
            )

        assert refused.value.code == ERR_COVER_SWITCH_REQUIRES_REVIEW
        assert switcher.commands == []
