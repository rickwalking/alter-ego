"""Slide-1 switches reopen an approved carousel's review, over fakes.

Gherkin: tests/features/reopen_review_on_cover_switch_ae0597.feature
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeVar
from uuid import UUID, uuid4

import pytest

from rag_backend.application.services.carousel import slide_cover_switch
from rag_backend.application.services.carousel.cover_review_switch import (
    ReviewSwitch,
    ReviewSwitchOutcome,
    render_refusal,
    review_refusal,
    switch_in_review,
)
from rag_backend.application.services.carousel.cover_switch_guard import (
    ReopenRefusedError,
    ReviewState,
)
from rag_backend.application.services.carousel.owner_autofix_lock import LockedWrite
from rag_backend.application.services.carousel.slide_cover_switch import (
    SlideCoverSwitchCommand,
    SlideCoverSwitchDeps,
    SlideCoverSwitchService,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_STATUS_CONFLICT,
    AUTOFIX_STATUS_FIXED,
)
from rag_backend.domain.constants.cover_autoselect import OUTCOME_AUTO_SELECT_SELECTED
from rag_backend.domain.constants.cover_review_switch import (
    ERR_COVER_SWITCH_REQUIRES_REVIEW,
    REASON_AUTO_SELECT_APPROVED,
    REASON_AUTO_SELECT_NOT_IN_REVIEW,
    REASON_AUTO_SELECT_PUBLISHED,
    REASON_AUTO_SELECT_ROLLBACK_FAILED,
    REASON_AUTO_SELECT_ROLLED_BACK,
    REASON_REVIEW_NOT_REOPENED,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.models.slide_cover import SlideCover
from tests.unit.application.cover_review_fakes import (
    APPROVED,
    RUN,
    Hold,
    Reads,
    ReviewStore,
    in_review,
    selecting,
)

_T = TypeVar("_T")
_PROJECT = str(uuid4())


@dataclass
class _Log:
    """The order of the switch's writes."""

    steps: list[str] = field(default_factory=list)


@dataclass
class _Repo:
    log: _Log
    project: CarouselProject = field(default_factory=lambda: in_review())
    updates: list[tuple[str, str]] = field(default_factory=list)

    async def get_project_by_id(self, project_id: UUID) -> CarouselProject | None:
        del project_id
        return self.project

    async def update_project(self, project: CarouselProject) -> CarouselProject:
        self.log.steps.append("update")
        self.updates.append((project.current_phase, project.phase_status))
        return project


@dataclass
class _Db:
    log: _Log

    async def commit(self) -> None:
        self.log.steps.append("commit")

    async def rollback(self) -> None:
        self.log.steps.append("rollback")


@dataclass
class _Marker:
    log: _Log

    async def mark(self, project_id: str) -> None:
        del project_id
        self.log.steps.append("mark")

    async def clear(self, project_id: str, rendered_from: datetime) -> None:
        del project_id, rendered_from
        self.log.steps.append("clear")


@dataclass
class _Reopener:
    log: _Log
    refusal: str = ""

    async def reopen(self, project_id: str) -> None:
        del project_id
        self.log.steps.append("reopen")
        if self.refusal:
            raise ReopenRefusedError(self.refusal)


@dataclass
class _Review:
    state: ReviewState

    async def review_state(self, project_id: str) -> ReviewState | None:
        del project_id
        return self.state


class _Stager:
    async def stage(self, project_id: str, cover: SlideCover) -> bool:
        del project_id, cover
        return True


@dataclass
class _Renderer:
    log: _Log

    async def render(self, project_id: str) -> tuple[str, ...]:
        del project_id
        self.log.steps.append("render")
        return ()


async def _locked(
    db: object, target: LockedWrite, write: Callable[[], Awaitable[_T]]
) -> _T:
    del db, target
    return await write()


def _service(
    state: ReviewState, *, reopen: bool
) -> tuple[SlideCoverSwitchService, _Log, _Repo]:
    log = _Log()
    repo = _Repo(log=log)
    service = SlideCoverSwitchService(
        SlideCoverSwitchDeps(
            db=_Db(log),
            repo=repo,
            stager=_Stager(),
            renderer=_Renderer(log),
            review=_Review(state),
            marker=_Marker(log),
            reopener=_Reopener(log) if reopen else None,
        )
    )
    return service, log, repo


def _command() -> SlideCoverSwitchCommand:
    cover = SlideCover(asset_id=uuid4(), kind="ai_image", staged_path="a.webp")
    return SlideCoverSwitchCommand(project_id=_PROJECT, expected_version=3, cover=cover)


_APPROVED_STATE = ReviewState(workflow_status=APPROVED, is_public=False)


@pytest.mark.unit
class TestSwitchService:
    # Scenario: A cover switch reopens the review of an approved carousel
    @pytest.mark.asyncio
    async def test_an_approved_carousel_is_reopened_in_one_commit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(slide_cover_switch, "write_locked", _locked)
        service, log, repo = _service(_APPROVED_STATE, reopen=True)

        result = await service.switch(_command())

        assert result.status == AUTOFIX_STATUS_FIXED
        assert result.reopened is True
        assert log.steps == ["mark", "reopen", "update", "commit", "render", "clear"]
        assert repo.updates == [("final_review", "awaiting_human")]

    # Scenario: A carousel waiting for its first approval switches and stays in review
    @pytest.mark.asyncio
    async def test_a_draft_carousel_is_not_reopened(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(slide_cover_switch, "write_locked", _locked)
        draft = ReviewState(workflow_status="draft", is_public=False)
        service, log, _repo = _service(draft, reopen=True)

        result = await service.switch(_command())

        assert result.reopened is False
        assert "reopen" not in log.steps
        assert log.steps[:3] == ["mark", "update", "commit"]

    # Scenario: A published carousel never changes
    # Scenario: A switch that cannot reopen the review refuses an approved carousel
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("state", "reopen"),
        [
            (ReviewState(workflow_status=APPROVED, is_public=True), True),
            (ReviewState(workflow_status="draft", is_public=True), True),
            (_APPROVED_STATE, False),
        ],
    )
    async def test_refused_writes_and_renders_nothing(
        self, monkeypatch: pytest.MonkeyPatch, state: ReviewState, reopen: bool
    ) -> None:
        monkeypatch.setattr(slide_cover_switch, "write_locked", _locked)
        service, log, repo = _service(state, reopen=reopen)

        result = await service.switch(_command())

        assert result.status == ERR_COVER_SWITCH_REQUIRES_REVIEW
        assert result.reopened is False
        assert log.steps == ["rollback"]
        assert repo.updates == []


@pytest.mark.unit
class TestRefusedReopen:
    # Scenario: A published carousel never changes
    # Scenario: A switch that cannot reopen the review refuses an approved carousel
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "reason", [REASON_AUTO_SELECT_PUBLISHED, REASON_REVIEW_NOT_REOPENED]
    )
    async def test_a_refused_reopen_rolls_everything_back(
        self, monkeypatch: pytest.MonkeyPatch, reason: str
    ) -> None:
        """Released under the lock, or a checkpoint that cannot reopen."""
        monkeypatch.setattr(slide_cover_switch, "write_locked", _locked)
        log = _Log()
        repo = _Repo(log=log)
        service = SlideCoverSwitchService(
            SlideCoverSwitchDeps(
                db=_Db(log),
                repo=repo,
                stager=_Stager(),
                renderer=_Renderer(log),
                review=_Review(_APPROVED_STATE),
                marker=_Marker(log),
                reopener=_Reopener(log, refusal=reason),
            )
        )

        result = await service.switch(_command())

        assert result.status == ERR_COVER_SWITCH_REQUIRES_REVIEW
        assert result.reopened is False
        assert log.steps == ["mark", "reopen", "rollback"]
        assert repo.updates == []


def _approved_at_final_review() -> Reads:
    project = in_review(phase_status="approved")
    return Reads(project, workflow_status=APPROVED)


@pytest.mark.unit
class TestReviewSwitch:
    # Scenario: A cover switch reopens the review of an approved carousel
    # Scenario: A reopened scheduled run keeps its time and gets a new review
    @pytest.mark.asyncio
    async def test_an_approved_carousel_switches_and_asks_for_a_review(self) -> None:
        reopened = ReviewSwitchOutcome(status=AUTOFIX_STATUS_FIXED, reopened=True)
        store, hold = ReviewStore(outcome=reopened), Hold(run_id=None)
        selector, selection = selecting(
            _approved_at_final_review(), ReviewSwitch(store=store, hold=hold)
        )

        assert await selector.select(selection) == OUTCOME_AUTO_SELECT_SELECTED
        assert len(store.writes) == 1
        assert hold.reopened_ids == ["p-1"]

    # Scenario: A rolled back switch keeps the review reopened
    @pytest.mark.asyncio
    async def test_a_rolled_back_reopen_still_asks_for_a_review(self) -> None:
        rolled = ReviewSwitchOutcome(
            status=REASON_AUTO_SELECT_ROLLED_BACK, reopened=True
        )
        hold = Hold()
        review = ReviewSwitch(store=ReviewStore(outcome=rolled), hold=hold)
        selector, selection = selecting(_approved_at_final_review(), review)

        assert await selector.select(selection) == REASON_AUTO_SELECT_ROLLED_BACK
        assert hold.released == [(RUN, True)]
        assert hold.reopened_ids == ["p-1"]

    # Scenario: A cover switch reopens the review of an approved carousel
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "outcome",
        [
            ReviewSwitchOutcome(status=AUTOFIX_STATUS_FIXED),
            ReviewSwitchOutcome(status=AUTOFIX_STATUS_CONFLICT),
            ReviewSwitchOutcome(status=REASON_AUTO_SELECT_ROLLED_BACK),
        ],
    )
    async def test_no_new_review_without_a_landed_reopen(
        self, outcome: ReviewSwitchOutcome
    ) -> None:
        hold = Hold()
        review = ReviewSwitch(store=ReviewStore(outcome=outcome), hold=hold)
        selector, selection = selecting(Reads(in_review()), review)

        await selector.select(selection)

        assert hold.reopened_ids == []

    # Scenario: A reopened scheduled run keeps its time and gets a new review
    @pytest.mark.asyncio
    async def test_a_failed_rollback_still_asks_for_a_review(self) -> None:
        """The approval was dropped: the held run is escalated, and the review
        is asked for anyway, so a scheduled run never expires silently."""
        failed = ReviewSwitchOutcome(
            status=REASON_AUTO_SELECT_ROLLBACK_FAILED, lock_version=9, reopened=True
        )
        hold = Hold()
        review = ReviewSwitch(store=ReviewStore(outcome=failed), hold=hold)
        selector, selection = selecting(_approved_at_final_review(), review)

        await selector.select(selection)

        assert hold.escalated == [(RUN, 9)]
        assert hold.reopened_ids == ["p-1"]

    # Scenario: A cover switch reopens the review of an approved carousel
    def test_review_and_render_refusals(self) -> None:
        from rag_backend.application.services.carousel.cover_autoselect import (
            ProjectAtVersion,
        )

        approved = ProjectAtVersion(
            project=in_review(phase_status="approved"),
            lock_version=3,
            workflow_status=APPROVED,
        )
        elsewhere = ProjectAtVersion(
            project=in_review(current_phase="images", phase_status="approved"),
            lock_version=3,
            workflow_status=APPROVED,
        )

        assert review_refusal(approved) is None
        assert review_refusal(elsewhere) == REASON_AUTO_SELECT_NOT_IN_REVIEW
        assert render_refusal(approved) == REASON_AUTO_SELECT_APPROVED
        assert render_refusal(elsewhere) == REASON_AUTO_SELECT_APPROVED

    # Scenario: A cover switch reopens the review of an approved carousel
    @pytest.mark.asyncio
    async def test_without_review_deps_nothing_is_switched(self) -> None:
        from rag_backend.application.services.carousel.cover_autoselect import (
            AutoCoverSelection,
            FoundCover,
            ProjectAtVersion,
        )

        found = ProjectAtVersion(
            project=in_review(), lock_version=3, workflow_status="draft"
        )
        selection = selecting(Reads(in_review()), None)[1]
        assert isinstance(selection, AutoCoverSelection)
        status = await switch_in_review(
            selection, FoundCover(found=found, asset_id=uuid4())
        )

        assert status == REASON_AUTO_SELECT_NOT_IN_REVIEW
