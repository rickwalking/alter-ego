"""The owner's "Tentar de novo" on an escalated run, and approve on a rejected one.

Feature: tests/features/carousel_owner_retry_ae0606.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import uuid4

import pytest

from rag_backend.modules.autopilot.application.owner_actions import (
    OwnerActionService,
)
from rag_backend.modules.autopilot.application.schedule_steps import refusal_text
from rag_backend.modules.autopilot.cover_constants import ANSWER_REVIEW_REPLACED
from rag_backend.modules.autopilot.domain.carousel_retry import (
    CarouselRetryOutcome,
    CarouselRetryRequest,
    carousel_retry_keyboard,
    parse_carousel_retry,
)
from rag_backend.modules.autopilot.domain.gate import GateSnapshot, ResumeStatus
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.editorial_driver import (
    _resume_status,
)
from rag_backend.modules.autopilot.recovery_constants import REASON_CAROUSEL_REJECTED
from rag_backend.modules.autopilot.webhook_constants import (
    TEXT_ALREADY,
    TEXT_APPROVE_CAROUSEL_REJECTED,
    TEXT_REJECTED,
)
from rag_backend.modules.editorial.public import PHASE_STATUS_REJECTED
from tests.unit.modules.autopilot.test_owner_actions import (
    _action,
    _handle,
    _snapshot,
    _tap,
    _World,
    _world,
)

_OWNER_USER = "owner-user"


@dataclass
class _Retrier:
    outcome: CarouselRetryOutcome
    requests: list[CarouselRetryRequest] = field(default_factory=list)

    async def retry(self, request: CarouselRetryRequest) -> CarouselRetryOutcome:
        self.requests.append(request)
        return self.outcome


def _with_retrier(world: _World, retrier: _Retrier | None) -> _World:
    deps = replace(
        world.service._deps, carousel_retrier=retrier, owner_user_id=_OWNER_USER
    )
    return replace(world, service=OwnerActionService(deps))


def _retry_tap(world: _World) -> str:
    return f"ap:cr:{world.runs.run.run_id}"


@pytest.mark.unit
class TestCarouselRetryTap:
    # Scenario: An escalated autopilot run moves back to generating
    async def test_an_accepted_retry_edits_the_message(self) -> None:
        retrier = _Retrier(CarouselRetryOutcome(accepted=True, phase="content"))
        world = _with_retrier(_world(), retrier)

        await _handle(world, _tap(1, _retry_tap(world)))

        assert retrier.requests == [
            CarouselRetryRequest(
                project_id=str(world.runs.run.carousel_project_id),
                actor_id=_OWNER_USER,
            )
        ]
        assert world.messenger.answers[-1].text == "Refazendo"
        assert world.messenger.edits[-1].text == "🔁 Refazendo a fase content…"

    # Scenario: A double tap ends in run_in_progress
    async def test_a_refused_retry_answers_with_its_own_text(self) -> None:
        refused = CarouselRetryOutcome(
            accepted=False, refusal="resume_already_in_progress"
        )
        world = _with_retrier(_world(), _Retrier(refused))

        await _handle(world, _tap(1, _retry_tap(world)))

        assert world.messenger.edits == []
        assert world.messenger.answers[-1].text == "Não foi possível tentar de novo"
        assert world.messenger.texts[-1].text == "Esta fase já está rodando."

    async def test_an_unknown_refusal_names_its_code(self) -> None:
        refused = CarouselRetryOutcome(accepted=False, refusal="concurrent_update")
        world = _with_retrier(_world(), _Retrier(refused))

        await _handle(world, _tap(1, _retry_tap(world)))

        assert "(concurrent_update)" in world.messenger.texts[-1].text

    async def test_without_a_retrier_the_tap_is_already_handled(self) -> None:
        world = _with_retrier(_world(), None)

        await _handle(world, _tap(1, _retry_tap(world)))

        assert world.messenger.edits[-1].text == TEXT_ALREADY

    async def test_an_unknown_run_is_already_handled(self) -> None:
        retrier = _Retrier(CarouselRetryOutcome(accepted=True))
        world = _with_retrier(_world(), retrier)

        await _handle(world, _tap(1, f"ap:cr:{uuid4()}"))

        assert retrier.requests == []
        assert world.messenger.edits[-1].text == TEXT_ALREADY

    # Scenario: A tap from someone who does not own the carousel changes nothing
    async def test_a_stranger_chat_reaches_nothing(self) -> None:
        retrier = _Retrier(CarouselRetryOutcome(accepted=True))
        world = _with_retrier(_world(), retrier)

        await _handle(world, _tap(1, _retry_tap(world), actor="stranger"))

        assert retrier.requests == []
        assert world.messenger.edits == []

    def test_the_button_round_trips_and_fits_telegram(self) -> None:
        run_id = uuid4()
        button = carousel_retry_keyboard(run_id).rows[0][0]

        assert button.text == "🔁 Tentar de novo"
        assert parse_carousel_retry(button.callback_data) == run_id
        assert len(button.callback_data.encode()) <= 64
        assert parse_carousel_retry(f"ap:retry:{run_id}") is None


def _rejected_at_tapped_revision(
    monkeypatch: pytest.MonkeyPatch, world: _World
) -> None:
    """The carousel is rejected and, unusually, still at the tapped revision 4."""

    async def _read_gate(project_id: str) -> GateSnapshot:
        del project_id
        return replace(_snapshot(), phase_status=PHASE_STATUS_REJECTED, lock_version=4)

    monkeypatch.setattr(world.editorial, "read_gate", _read_gate)


@pytest.mark.unit
class TestApproveOnRejected:
    # Scenario: A Telegram approve on a rejected carousel is refused
    @pytest.mark.parametrize("kind", ["approve", "pubnow", "sched"])
    async def test_a_current_revision_tap_never_approves(
        self, monkeypatch: pytest.MonkeyPatch, kind: str
    ) -> None:
        world = _world()
        _rejected_at_tapped_revision(monkeypatch, world)

        await _handle(world, _tap(1, _action(kind, world)))

        assert world.editorial.resumes == []
        assert world.release.ids == []
        assert world.runs.run.state is AutopilotRunState.REJECTED
        assert world.runs.run.state_reason == REASON_CAROUSEL_REJECTED
        assert world.messenger.answers[-1].text == ANSWER_REVIEW_REPLACED
        assert world.messenger.edits[-1].text == TEXT_REJECTED

    # Scenario: An unattended approve on a rejected carousel is refused
    def test_the_editorial_refusal_maps_to_its_own_status_and_text(self) -> None:
        status = _resume_status(ValueError("carousel_rejected"))

        assert status is ResumeStatus.CAROUSEL_REJECTED
        assert refusal_text(ResumeStatus.CAROUSEL_REJECTED) == (
            TEXT_APPROVE_CAROUSEL_REJECTED
        )
