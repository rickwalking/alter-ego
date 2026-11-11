"""The site's "Publicar agora" approval of a carousel at final review.

Gherkin: tests/features/instagram_publish_from_final_review_ae0624.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.modules.autopilot import approve_for_site_publish
from rag_backend.modules.autopilot.application.owner_approval import (
    FinalReviewApproval,
)
from rag_backend.modules.autopilot.application.site_publish import (
    SitePublishApproval,
    SitePublishDeps,
)
from rag_backend.modules.autopilot.domain.gate import ResumeStatus
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.ports import AutopilotRunRepository

_S = AutopilotRunState
_PROJECT = "project-1"


def _run(state: AutopilotRunState) -> AutopilotRun:
    return AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id=_PROJECT,
        state=state,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )


@dataclass
class _Runs:
    """One run (or none), moved by compare-and-set like the repository."""

    run: AutopilotRun | None
    moves: list[tuple[AutopilotRunState, AutopilotRunState]] = field(
        default_factory=list
    )
    lose_cas: bool = False

    async def find_by_carousel(self, project_id: str) -> AutopilotRun | None:
        del project_id
        return self.run

    async def transition(self, command: TransitionCommand) -> bool:
        if self.lose_cas or self.run is None or self.run.state is not command.expected:
            return False
        self.moves.append((command.expected, command.new))
        self.run = replace(self.run, state=command.new)
        return True


@dataclass
class _Approval:
    """The final-review approve and the release, recorded."""

    status: ResumeStatus = ResumeStatus.APPLIED
    released: bool = True
    calls: list[str] = field(default_factory=list)

    async def approve(self, run: AutopilotRun) -> ResumeStatus:
        self.calls.append(f"approve:{run.carousel_project_id}")
        return self.status

    async def approve_project(self, project_id: str) -> ResumeStatus:
        self.calls.append(f"approve_project:{project_id}")
        return self.status

    async def release(self, run: AutopilotRun) -> bool:
        self.calls.append(f"release:{run.carousel_project_id}")
        return self.released


def _service(runs: _Runs, approval: _Approval) -> SitePublishApproval:
    return SitePublishApproval(
        SitePublishDeps(
            runs=cast(AutopilotRunRepository, runs),
            approval=cast(FinalReviewApproval, approval),
        )
    )


@pytest.mark.unit
class TestSitePublishApproval:
    # Scenario: A carousel at final review without an autopilot run is approved and published
    @pytest.mark.asyncio
    async def test_without_run_approves_the_final_review(self) -> None:
        approval = _Approval()
        assert await _service(_Runs(run=None), approval).approve_for_publish(_PROJECT)
        assert approval.calls == [f"approve_project:{_PROJECT}"]

    # Scenario: A refused final-review approve publishes nothing
    @pytest.mark.asyncio
    async def test_without_run_refused_approve(self) -> None:
        approval = _Approval(status=ResumeStatus.VERSION_CONFLICT)
        service = _service(_Runs(run=None), approval)
        assert not await service.approve_for_publish(_PROJECT)

    # Scenario: An autopilot carousel awaiting the owner is published like "Publicar agora"
    @pytest.mark.asyncio
    async def test_awaiting_owner_run_moves_approves_and_releases(self) -> None:
        runs = _Runs(run=_run(_S.AWAITING_OWNER))
        approval = _Approval()
        assert await _service(runs, approval).approve_for_publish(_PROJECT)
        assert runs.moves == [(_S.AWAITING_OWNER, _S.PUBLISHING)]
        assert approval.calls == [f"approve:{_PROJECT}", f"release:{_PROJECT}"]

    # Scenario: A refused final-review approve publishes nothing
    @pytest.mark.asyncio
    async def test_refused_approve_puts_the_run_back(self) -> None:
        runs = _Runs(run=_run(_S.AWAITING_OWNER))
        approval = _Approval(status=ResumeStatus.RENDER_PENDING)
        assert not await _service(runs, approval).approve_for_publish(_PROJECT)
        assert runs.moves == [
            (_S.AWAITING_OWNER, _S.PUBLISHING),
            (_S.PUBLISHING, _S.AWAITING_OWNER),
        ]
        assert approval.calls == [f"approve:{_PROJECT}"]

    # Scenario: A failed release marks the run failed
    @pytest.mark.asyncio
    async def test_failed_release_marks_the_run_failed(self) -> None:
        runs = _Runs(run=_run(_S.AWAITING_OWNER))
        approval = _Approval(released=False)
        assert not await _service(runs, approval).approve_for_publish(_PROJECT)
        assert runs.moves[-1] == (_S.PUBLISHING, _S.PUBLISH_FAILED)

    # Scenario: A scheduled autopilot carousel is published now
    @pytest.mark.asyncio
    async def test_scheduled_run_is_published_now(self) -> None:
        runs = _Runs(run=_run(_S.SCHEDULED))
        approval = _Approval()
        assert await _service(runs, approval).approve_for_publish(_PROJECT)
        assert runs.moves == [(_S.SCHEDULED, _S.PUBLISHING)]
        assert approval.calls == [f"release:{_PROJECT}"]

    # Scenario: A scheduled autopilot carousel is published now
    @pytest.mark.asyncio
    async def test_scheduled_run_with_a_failed_release(self) -> None:
        runs = _Runs(run=_run(_S.SCHEDULED))
        approval = _Approval(released=False)
        assert not await _service(runs, approval).approve_for_publish(_PROJECT)
        assert runs.moves[-1] == (_S.PUBLISHING, _S.PUBLISH_FAILED)

    # Scenario: Runs that are not waiting for the owner are not published now
    @pytest.mark.asyncio
    async def test_publishing_run_goes_through_its_own_claim(self) -> None:
        runs = _Runs(run=_run(_S.PUBLISHING))
        approval = _Approval()
        assert await _service(runs, approval).approve_for_publish(_PROJECT)
        assert runs.moves == []
        assert approval.calls == []

    # Scenario: Runs that are not waiting for the owner are not published now
    @pytest.mark.parametrize(
        "state", [_S.GENERATING, _S.REWORKING, _S.PUBLISHED, _S.REJECTED]
    )
    @pytest.mark.asyncio
    async def test_other_runs_are_refused(self, state: AutopilotRunState) -> None:
        runs = _Runs(run=_run(state))
        approval = _Approval()
        assert not await _service(runs, approval).approve_for_publish(_PROJECT)
        assert runs.moves == []
        assert approval.calls == []

    # Scenario: An autopilot carousel awaiting the owner is published like "Publicar agora"
    @pytest.mark.asyncio
    async def test_a_lost_compare_and_set_refuses(self) -> None:
        """A Telegram tap moved the run first: the site click changes nothing."""
        runs = _Runs(run=_run(_S.AWAITING_OWNER), lose_cas=True)
        approval = _Approval()
        assert not await _service(runs, approval).approve_for_publish(_PROJECT)
        assert approval.calls == []


@pytest.mark.unit
class TestApproveForSitePublish:
    # Scenario: A refused final-review approve publishes nothing
    @pytest.mark.asyncio
    async def test_unwired_engine_refuses(self) -> None:
        """Without the editorial engine on the app state nothing is approved."""
        session = cast(AsyncSession, SimpleNamespace())
        assert not await approve_for_site_publish(session, SimpleNamespace(), _PROJECT)
