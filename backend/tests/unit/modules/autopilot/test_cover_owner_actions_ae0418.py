"""Owner taps on "Usar capa do Grok" and back (AE-0418, ADR-0024).

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
  Scenario: "Usar capa do Grok" at the thesis switches slide 1 to the cover, and back
  Scenario: A second tap of the same choice changes nothing
  Scenario: The Radar IA review offers the cover and swaps slide 1
  Scenario: A cover tap on a run that is not waiting is refused
  Scenario: A non-owner cover tap is ignored
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import UUID, uuid4

import pytest

from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.modules.autopilot.application.owner_actions import (
    OwnerActionDeps,
    OwnerActionService,
)
from rag_backend.modules.autopilot.cover_constants import (
    ANSWER_COVER_NOT_NOW,
    ANSWER_COVER_OFF,
    ANSWER_COVER_ON,
    ANSWER_COVER_SAME,
    COVER_REWORK_PHASE,
    TEXT_COVER_SWITCHING,
)
from rag_backend.modules.autopilot.domain.cover_offer import CoverOffer
from rag_backend.modules.autopilot.domain.cover_ports import CoverChoiceCommand
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.webhook_update import WebhookUpdate
from tests.unit.modules.autopilot.test_autopilot_runner import _Recovery
from tests.unit.modules.autopilot.test_owner_actions import (
    _Claims,
    _Clock,
    _Editorial,
    _Messenger,
    _Pending,
    _Release,
    _tap,
)
from tests.unit.modules.autopilot.test_thesis_owner_actions_ae0377 import (
    _DraftTopics,
    _topic,
)

_OWNER = "42"
_S = AutopilotRunState


@dataclass
class _Runs:
    run: AutopilotRun

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        return self.run if self.run.run_id == run_id else None

    async def transition(self, command: TransitionCommand) -> bool:
        if self.run.state is not command.expected:
            return False
        self.run = replace(self.run, state=command.new, state_reason=command.reason)
        return True


@dataclass
class _Choices:
    runs: _Runs
    commands: list[CoverChoiceCommand] = field(default_factory=list)
    lose: bool = False

    async def set_cover_choice(self, command: CoverChoiceCommand) -> bool:
        self.commands.append(command)
        if self.lose or self.runs.run.state is not command.expected:
            return False
        self.runs.run = replace(self.runs.run, cover_chosen=command.chosen)
        return True


@dataclass
class _Offers:
    offer_for: CoverOffer | None

    async def offer(self, run: AutopilotRun) -> CoverOffer | None:
        if self.offer_for is None:
            return None
        return replace(self.offer_for, chosen=run.cover_chosen)

    async def chosen_cover(self, run: AutopilotRun) -> SlideCover | None:
        del run
        return None


@dataclass
class _World:
    runs: _Runs
    choices: _Choices
    offers: _Offers
    messenger: _Messenger
    recovery: _Recovery
    service: OwnerActionService


def _offer(*, pov: bool = True) -> CoverOffer:
    return CoverOffer(
        kind="ai_image", credit="", chosen=False, pov=pov, photo_path="/c.webp"
    )


def _world(
    state: AutopilotRunState,
    *,
    project: str | None = None,
    offer: CoverOffer | None = None,
    wired: bool = True,
) -> _World:
    run = AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id=project,
        state=state,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )
    runs = _Runs(run=run)
    choices = _Choices(runs=runs)
    messenger = _Messenger()
    recovery = _Recovery(runs=runs)
    offers = _Offers(offer_for=offer if offer is not None else _offer())
    service = OwnerActionService(
        OwnerActionDeps(
            runs=runs,
            updates=_Claims(),
            pending=_Pending(),
            editorial=_Editorial(),
            release=_Release(),
            messenger=messenger,
            recovery=recovery,
            clock=_Clock(),
            owner_chat_id=_OWNER,
            topics=_DraftTopics(topic=_topic("A tese do scout.")),
            covers=offers,
            cover_choices=choices if wired else None,
        )
    )
    return _World(
        runs=runs,
        choices=choices,
        offers=offers,
        messenger=messenger,
        recovery=recovery,
        service=service,
    )


async def _tap_cover(
    world: _World, kind: str, update_id: int = 1, actor: str = _OWNER
) -> None:
    update: WebhookUpdate = _tap(update_id, f"ap:{kind}:{world.runs.run.run_id}", actor)
    await world.service.handle(update)
    await world.service.deliver()


def _answers(world: _World) -> list[str]:
    return [answer.text for answer in world.messenger.answers]


@pytest.mark.unit
class TestThesisCover:
    @pytest.mark.asyncio
    async def test_use_cover_then_back_to_the_photo(self) -> None:
        world = _world(_S.AWAITING_THESIS)
        await _tap_cover(world, "cv")
        assert world.runs.run.cover_chosen
        assert world.runs.run.state is _S.AWAITING_THESIS
        assert _answers(world) == [ANSWER_COVER_ON]
        edit = world.messenger.edits[-1]
        assert "A tese do scout." in edit.text
        assert edit.keyboard is not None
        assert edit.keyboard.rows[-1][0].text == "📸 Usar minha foto"

        await _tap_cover(world, "cvoff", update_id=2)
        assert not world.runs.run.cover_chosen
        assert _answers(world)[-1] == ANSWER_COVER_OFF
        last = world.messenger.edits[-1].keyboard
        assert last is not None
        assert last.rows[-1][0].text == "🖼️ Usar capa do Grok"

    @pytest.mark.asyncio
    async def test_second_tap_of_the_same_choice_changes_nothing(self) -> None:
        world = _world(_S.AWAITING_THESIS)
        await _tap_cover(world, "cv")
        await _tap_cover(world, "cv", update_id=2)
        assert _answers(world)[-1] == ANSWER_COVER_SAME
        assert len(world.choices.commands) == 1

    @pytest.mark.asyncio
    async def test_lost_compare_and_set_is_not_now(self) -> None:
        world = _world(_S.AWAITING_THESIS)
        world.choices.lose = True
        await _tap_cover(world, "cv")
        assert _answers(world) == [ANSWER_COVER_NOT_NOW]
        assert world.messenger.edits == []


@pytest.mark.unit
class TestReviewCover:
    @pytest.mark.asyncio
    async def test_review_tap_queues_the_cover_rework(self) -> None:
        world = _world(_S.AWAITING_OWNER, project="p-1", offer=_offer(pov=False))
        await _tap_cover(world, "cv")
        assert world.runs.run.state is _S.REWORKING
        assert world.runs.run.cover_chosen
        assert world.runs.run.rework_phase == COVER_REWORK_PHASE
        assert _answers(world) == [ANSWER_COVER_ON]
        assert world.messenger.edits[-1].text == TEXT_COVER_SWITCHING

    @pytest.mark.asyncio
    async def test_review_without_a_project_is_not_now(self) -> None:
        world = _world(_S.AWAITING_OWNER)
        await _tap_cover(world, "cv")
        assert world.runs.run.state is _S.AWAITING_OWNER
        assert _answers(world) == [ANSWER_COVER_NOT_NOW]


@pytest.mark.unit
class TestRefusals:
    @pytest.mark.asyncio
    async def test_run_in_another_state_is_unchanged(self) -> None:
        world = _world(_S.GENERATING, project="p-1")
        await _tap_cover(world, "cv")
        assert world.runs.run.state is _S.GENERATING
        assert not world.runs.run.cover_chosen
        assert _answers(world) == [ANSWER_COVER_NOT_NOW]

    @pytest.mark.asyncio
    async def test_non_owner_is_ignored(self) -> None:
        world = _world(_S.AWAITING_THESIS)
        await _tap_cover(world, "cv", actor="999")
        assert not world.runs.run.cover_chosen
        assert world.messenger.answers == []

    @pytest.mark.asyncio
    async def test_no_offer_or_unwired_is_not_now(self) -> None:
        unwired = _world(_S.AWAITING_THESIS, wired=False)
        await _tap_cover(unwired, "cv")
        assert _answers(unwired) == [ANSWER_COVER_NOT_NOW]

        world = _world(_S.AWAITING_THESIS)
        world.offers.offer_for = None
        await _tap_cover(world, "cv")
        assert _answers(world) == [ANSWER_COVER_NOT_NOW]
        assert not world.runs.run.cover_chosen

    @pytest.mark.asyncio
    async def test_unknown_run_is_not_now(self) -> None:
        world = _world(_S.AWAITING_THESIS)
        update = _tap(1, f"ap:cv:{uuid4()}")
        await world.service.handle(update)
        await world.service.deliver()
        assert _answers(world) == [ANSWER_COVER_NOT_NOW]
