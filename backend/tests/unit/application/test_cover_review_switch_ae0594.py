"""The review switch of a website cover over fakes.

Gherkin: tests/features/website_cover_review_switch_ae0594.feature
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from structlog.testing import capture_logs

from rag_backend.application.services.carousel.cover_autoselect import (
    AutoCoverSelection,
    AutoCoverSelector,
    AutoCoverWrite,
    CoverBaseline,
    ProjectAtVersion,
)
from rag_backend.application.services.carousel.cover_review_switch import (
    ReviewSwitch,
    ReviewSwitchOutcome,
    switch_in_review,
)
from rag_backend.domain.constants.carousel_autofix import AUTOFIX_STATUS_CONFLICT
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
    REASON_AUTO_SELECT_APPROVED,
    REASON_AUTO_SELECT_NOT_IN_REVIEW,
    REASON_AUTO_SELECT_PUBLISHED,
    REASON_AUTO_SELECT_ROLLED_BACK,
)
from rag_backend.domain.models import CarouselStatus
from rag_backend.domain.models.slide_cover import SlideCover
from tests.unit.application.cover_review_fakes import (
    APPROVED,
    ASSET,
    BASELINE,
    GENERATION,
    HOOK,
    RUN,
    Hold,
    NoReviewHold,
    Reads,
    ReviewStore,
    in_review,
    selecting,
)


def _reasons(logs: list[dict[str, object]]) -> list[object]:
    return [e.get("reason") for e in logs if e["event"] == LOG_COVER_AUTO_SELECT]


@pytest.mark.unit
class TestReviewSwitch:
    # Scenario: A website cover switches a completed carousel in final review
    # Scenario: The Telegram review is held while slide 1 changes
    @pytest.mark.asyncio
    async def test_switches_a_completed_carousel_in_review(self) -> None:
        store, hold = ReviewStore(), Hold()
        review = ReviewSwitch(store=store, hold=hold)
        selector, selection = selecting(Reads(in_review()), review)

        outcome = await selector.select(selection)

        assert outcome == OUTCOME_AUTO_SELECT_SELECTED
        assert store.writes == [
            AutoCoverWrite(
                project_id="p-1", asset_id=ASSET, expected_version=7, baseline=BASELINE
            )
        ]
        assert hold.held == ["p-1"]
        assert hold.released == [(RUN, True)]

    # Scenario: A failed or overtaken website cover switch is rolled back
    @pytest.mark.asyncio
    async def test_a_rolled_back_switch_is_logged_and_sends_the_review(self) -> None:
        rolled = ReviewSwitchOutcome(
            status=REASON_AUTO_SELECT_ROLLED_BACK, render_errors=("x",)
        )
        hold = Hold()
        review = ReviewSwitch(store=ReviewStore(outcome=rolled), hold=hold)
        selector, selection = selecting(Reads(in_review()), review)

        with capture_logs() as logs:
            outcome = await selector.select(selection)

        assert outcome == REASON_AUTO_SELECT_ROLLED_BACK
        assert _reasons(logs) == [REASON_AUTO_SELECT_ROLLED_BACK]
        assert hold.released == [(RUN, True)]

    # Scenario: A lock conflict on a completed carousel is skipped and logged
    @pytest.mark.asyncio
    async def test_a_conflict_is_skipped_and_the_review_handed_back(self) -> None:
        conflict = ReviewSwitchOutcome(status=AUTOFIX_STATUS_CONFLICT)
        hold = Hold()
        review = ReviewSwitch(store=ReviewStore(outcome=conflict), hold=hold)
        selector, selection = selecting(Reads(in_review()), review)

        with capture_logs() as logs:
            outcome = await selector.select(selection)

        assert outcome == REASON_AUTO_SELECT_CONFLICT
        assert _reasons(logs) == [REASON_AUTO_SELECT_CONFLICT]
        assert hold.released == [(RUN, False)]

    # Scenario: The Telegram review is held while slide 1 changes
    @pytest.mark.asyncio
    async def test_a_store_crash_releases_as_changed(self) -> None:
        hold = Hold()
        review = ReviewSwitch(store=ReviewStore(error=RuntimeError("boom")), hold=hold)
        selector, selection = selecting(Reads(in_review()), review)

        with pytest.raises(RuntimeError, match="boom"):
            await selector.select(selection)

        assert hold.released == [(RUN, True)]

    # Scenario: A website cover switches a completed carousel in final review
    @pytest.mark.asyncio
    async def test_no_held_run_is_never_released(self) -> None:
        hold = Hold(run_id=None)
        review = ReviewSwitch(store=ReviewStore(), hold=hold)
        selector, selection = selecting(Reads(in_review()), review)

        assert await selector.select(selection) == OUTCOME_AUTO_SELECT_SELECTED
        assert hold.released == []

    # Scenario: A website cover on an approved or scheduled carousel stays a picker option
    # Scenario: A website cover on a published carousel stays a picker option
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("reads", "reason"),
        [
            (Reads(in_review(), workflow_status=APPROVED), REASON_AUTO_SELECT_APPROVED),
            (Reads(in_review(is_public=True)), REASON_AUTO_SELECT_PUBLISHED),
            (
                Reads(in_review(current_phase="images")),
                REASON_AUTO_SELECT_NOT_IN_REVIEW,
            ),
            (
                Reads(in_review(phase_status="approved")),
                REASON_AUTO_SELECT_NOT_IN_REVIEW,
            ),
            (Reads(in_review(phase_status="rejected")), REASON_AUTO_SELECT_FAILED),
        ],
    )
    async def test_refusals_never_hold_or_write(
        self, reads: Reads, reason: str
    ) -> None:
        store, hold = ReviewStore(), Hold()
        selector, selection = selecting(reads, ReviewSwitch(store=store, hold=hold))

        with capture_logs() as logs:
            outcome = await selector.select(selection)

        assert outcome == reason
        assert _reasons(logs) == [reason]
        assert store.writes == []
        assert hold.held == []

    # Scenario: A cover the owner chose while the job ran wins on a completed carousel
    @pytest.mark.asyncio
    async def test_a_change_since_the_baseline_wins(self) -> None:
        store, hold = ReviewStore(), Hold()
        moved = Reads(in_review(hook_asset_id=uuid4()))
        selector, selection = selecting(moved, ReviewSwitch(store=store, hold=hold))

        assert await selector.select(selection) == REASON_AUTO_SELECT_MANUAL_CHOICE
        assert store.writes == []
        assert hold.held == []

    # Scenario: A website cover switches a completed carousel in final review
    @pytest.mark.asyncio
    async def test_a_cover_chosen_before_the_job_does_not_block(self) -> None:
        chosen = SlideCover(asset_id=uuid4(), kind="ai_image", staged_path="c.webp")
        baseline = CoverBaseline(
            slide_cover_asset_id=chosen.asset_id, hook_asset_id=HOOK
        )
        store = ReviewStore()
        selection = AutoCoverSelection(
            project_id="p-1",
            generation_id=GENERATION,
            baseline=baseline,
            review=ReviewSwitch(store=store, hold=NoReviewHold()),
        )
        selector = AutoCoverSelector(Reads(in_review(slide_cover=chosen)))

        assert await selector.select(selection) == OUTCOME_AUTO_SELECT_SELECTED
        assert len(store.writes) == 1

    # Scenario: Replaying a website cover success changes nothing
    @pytest.mark.asyncio
    async def test_a_replay_is_already_selected(self) -> None:
        already = SlideCover(asset_id=ASSET, kind="ai_image", staged_path="c.webp")
        store, hold = ReviewStore(), Hold()
        reads = Reads(in_review(slide_cover=already))
        selector, selection = selecting(reads, ReviewSwitch(store=store, hold=hold))

        assert await selector.select(selection) == OUTCOME_AUTO_SELECT_ALREADY
        assert store.writes == []
        assert hold.held == []

    # Scenario: An autopilot cover on a completed carousel is unchanged
    @pytest.mark.asyncio
    async def test_without_a_review_switch_a_completed_carousel_is_skipped(
        self,
    ) -> None:
        reads = Reads(in_review())
        selector, selection = selecting(reads, None)

        assert await selector.select(selection) == REASON_AUTO_SELECT_COMPLETED
        assert reads.writes == []

    # Scenario: A website cover switches a completed carousel in final review
    @pytest.mark.asyncio
    async def test_a_carousel_before_its_review_keeps_the_gate_write(self) -> None:
        drafting = in_review(status=CarouselStatus.DRAFTING, current_phase="content")
        reads, store = Reads(drafting), ReviewStore()
        review = ReviewSwitch(store=store, hold=NoReviewHold())
        selector, selection = selecting(reads, review)

        assert await selector.select(selection) == OUTCOME_AUTO_SELECT_SELECTED
        assert len(reads.writes) == 1
        assert store.writes == []

    # Scenario: A website cover switches a completed carousel in final review
    @pytest.mark.asyncio
    async def test_switch_without_review_deps_is_refused(self) -> None:
        selection = AutoCoverSelection(
            project_id="p-1", generation_id=GENERATION, baseline=BASELINE
        )
        found = ProjectAtVersion(project=in_review(), lock_version=7)

        result = await switch_in_review(selection, (found, ASSET))

        assert result == REASON_AUTO_SELECT_NOT_IN_REVIEW
