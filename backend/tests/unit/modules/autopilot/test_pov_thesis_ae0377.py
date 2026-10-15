"""Autopilot POV topics, the thesis gate and POV slots (AE-0377).

Gherkin: tests/features/autopilot_pov_thesis.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.modules.autopilot.application.run_spec import project_spec
from rag_backend.modules.autopilot.application.thesis_prompts import (
    ThesisPromptDependencies,
    ThesisPromptService,
)
from rag_backend.modules.autopilot.domain.exceptions import TelegramDeliveryError
from rag_backend.modules.autopilot.domain.intake import (
    IntakeFacts,
    IntakePlan,
    ProposalInput,
    plan_intake,
    prepare,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
)
from rag_backend.modules.autopilot.domain.notify import (
    SaveNoticeLog,
    StatusNotice,
    StatusSendResult,
)
from rag_backend.modules.autopilot.domain.pov_schedule import (
    PovPublishSlots,
    sao_paulo_week,
    slot_policy_for,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.state_machine import ALLOWED_TRANSITIONS
from rag_backend.modules.autopilot.domain.thesis import (
    clean_thesis,
    needs_thesis,
    parse_thesis_callback,
    thesis_keyboard,
)

_URL = "https://x.com/openai/status/2010000000000000001"
_THESIS = "A IA escreve código; decidir o que construir continua sendo do dev."
_S = AutopilotRunState


def _proposal(**changes: object) -> ProposalInput:
    fields: dict[str, object] = {
        "title": "Agents that ship code",
        "angle": "What changes for builders",
        "why_viral": "Debated on X",
        "audience": "developers",
        "niche": "AI agents",
        "brief": "Why agents that ship code matter for builders.",
        "sources": (_URL,),
        "score": 80,
    }
    fields.update(changes)
    return ProposalInput(**fields)


def _facts(**changes: object) -> IntakeFacts:
    fields: dict[str, object] = {
        "allowlist": frozenset({_URL}),
        "known_hashes": {},
        "carousel_topics": (),
        "runs_today": 0,
        "daily_cap": 3,
    }
    fields.update(changes)
    return IntakeFacts(**fields)


def _plan(*proposals: ProposalInput, **facts: object) -> IntakePlan:
    return plan_intake(tuple(prepare(p) for p in proposals), _facts(**facts))


@pytest.mark.unit
class TestIntake:
    # Scenario: A v2 proposal is Radar IA
    def test_v2_proposal_is_news(self) -> None:
        plan = _plan(_proposal())
        assert plan.rejected == ()
        candidate = plan.new_candidates[0]
        assert candidate.proposal.content_mode == "news_analysis"
        assert candidate.queue

    # Scenario: POV without a draft thesis
    @pytest.mark.parametrize("thesis", [None, "   "])
    def test_pov_needs_thesis(self, thesis: str | None) -> None:
        plan = _plan(_proposal(content_mode="pov", thesis_draft=thesis))
        assert [r.reason for r in plan.rejected] == ["thesis_missing"]

    def test_pov_with_thesis_is_queued(self) -> None:
        plan = _plan(
            _proposal(content_mode="pov", thesis_draft=_THESIS),
            news_runs_this_week=1,
        )
        assert plan.rejected == ()
        assert plan.new_candidates[0].queue
        assert plan.new_candidates[0].proposal.thesis_draft == _THESIS

    # Scenario: Second Radar IA run in the same week
    def test_weekly_news_cap(self) -> None:
        plan = _plan(_proposal(), news_runs_this_week=1)
        assert [r.reason for r in plan.rejected] == ["weekly_news_cap_reached"]

    # Scenario: Only one Radar IA run is queued per week
    def test_one_news_queued_per_batch(self) -> None:
        plan = _plan(
            _proposal(title="Agents that ship code", score=60),
            _proposal(
                title="Models that ship tests",
                brief="Models that ship tests change review.",
                score=90,
            ),
            _proposal(
                title="Code review with agents",
                brief="Code review with agents, the owner's view.",
                content_mode="pov",
                thesis_draft=_THESIS,
                score=10,
            ),
        )
        queued = {c.proposal.title: c.queue for c in plan.new_candidates}
        assert queued == {
            "Agents that ship code": False,
            "Models that ship tests": True,
            "Code review with agents": True,
        }

    # Scenario: A draft thesis with a URL is rejected
    def test_url_in_thesis(self) -> None:
        plan = _plan(_proposal(content_mode="pov", thesis_draft=f"Veja {_URL}"))
        assert [r.reason for r in plan.rejected] == ["url_in_text"]


def _topic(**changes: object) -> TopicCandidate:
    fields: dict[str, object] = {
        "candidate_id": uuid4(),
        "title": "Agents that ship code",
        "angle": "a",
        "why_viral": "w",
        "audience": "developers",
        "niche": "AI agents",
        "brief": "b",
        "sources": (_URL,),
        "score": 80,
        "signal_hash": "h",
        "status": "accepted",
        "content_mode": "pov",
        "thesis_draft": _THESIS,
    }
    fields.update(changes)
    return TopicCandidate(**fields)


def _run(state: AutopilotRunState = _S.QUEUED, **changes: object) -> AutopilotRun:
    run = AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id=None,
        state=state,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )
    return replace(run, **changes)


@pytest.mark.unit
class TestThesisDomain:
    def test_state_machine(self) -> None:
        for pair in (
            (_S.QUEUED, _S.AWAITING_THESIS),
            (_S.AWAITING_THESIS, _S.QUEUED),
            (_S.AWAITING_THESIS, _S.REJECTED),
            (_S.AWAITING_THESIS, _S.EXPIRED),
        ):
            assert pair in ALLOWED_TRANSITIONS
        assert (_S.AWAITING_THESIS, _S.GENERATING) not in ALLOWED_TRANSITIONS

    # Scenario: A POV run waits for the thesis
    def test_needs_thesis(self) -> None:
        assert needs_thesis(_run(), _topic())
        assert not needs_thesis(_run(pov_thesis=_THESIS), _topic())
        assert not needs_thesis(_run(), _topic(content_mode=None))

    def test_clean_thesis(self) -> None:
        assert clean_thesis("  Uma   tese  ") == "Uma tese"
        assert clean_thesis("   ") is None
        assert clean_thesis("x" * 281) is None
        assert clean_thesis("x" * 280) == "x" * 280

    def test_callbacks_fit_and_parse(self) -> None:
        run_id = uuid4()
        keyboard = thesis_keyboard(run_id)
        datas = [b.callback_data for b in keyboard.rows[0]]
        assert all(len(d.encode()) <= 64 for d in datas)
        kinds = [parse_thesis_callback(d) for d in datas]
        assert [k.kind for k in kinds if k] == ["thok", "thed", "thno"]
        assert all(k is not None and k.run_id == run_id for k in kinds)
        assert parse_thesis_callback(f"ap:approve:{run_id}") is None

    # Scenario: A confirmed POV run starts generating
    def test_pov_spec(self) -> None:
        spec = project_spec(_run(pov_thesis=_THESIS), _topic(), "owner")
        assert spec.content_mode == "pov"
        assert spec.pov_thesis == _THESIS
        assert spec.image_style == "pov_editorial"

    def test_news_spec(self) -> None:
        spec = project_spec(
            _run(pov_thesis="ignored"),
            _topic(content_mode=None, image_style="neo_anime"),
            "owner",
        )
        assert spec.content_mode == "news_analysis"
        assert spec.pov_thesis is None
        assert spec.image_style == "neo_anime"


@dataclass
class _Store:
    """Runs + topics + notice ledger + notifier for the prompt service."""

    run: AutopilotRun
    topic: TopicCandidate | None
    sent: list[StatusNotice] = field(default_factory=list)
    saved: list[SaveNoticeLog] = field(default_factory=list)

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        return [self.run] if self.run.state is query.state else []

    async def get_topic(self, candidate_id: UUID) -> TopicCandidate | None:
        del candidate_id
        return self.topic

    async def save(self, command: SaveNoticeLog) -> None:
        self.saved.append(command)
        self.run = replace(self.run, notice_log=command.log)

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        self.sent.append(notice)
        return StatusSendResult(message_id=77)


@dataclass
class _DownStore(_Store):
    """Telegram is down: every send fails."""

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        del notice
        raise TelegramDeliveryError("telegram down")


def _prompts(store: _Store, configured: bool = True) -> ThesisPromptService:
    return ThesisPromptService(
        ThesisPromptDependencies(
            runs=store,
            topics=store,
            notices=store,
            notifier=store,
            chat_id="42",
            configured=configured,
        )
    )


@pytest.mark.unit
class TestThesisPrompt:
    # Scenario: The owner is asked once
    @pytest.mark.asyncio
    async def test_prompt_sent_once(self) -> None:
        store = _Store(run=_run(_S.AWAITING_THESIS), topic=_topic())
        assert await _prompts(store).tick() == 1
        assert await _prompts(store).tick() == 0
        assert len(store.sent) == 1
        notice = store.sent[0]
        assert _THESIS in notice.text
        assert "Agents that ship code" in notice.text
        assert notice.keyboard is not None
        assert [b.text for b in notice.keyboard.rows[0]] == [
            "✅ Confirmar",
            "✏️ Editar",
            "❌ Descartar",
        ]

    @pytest.mark.asyncio
    async def test_unconfigured_or_missing_topic(self) -> None:
        store = _Store(run=_run(_S.AWAITING_THESIS), topic=None)
        assert await _prompts(store, configured=False).tick() == 0
        assert await _prompts(store).tick() == 0
        assert store.sent == []

    @pytest.mark.asyncio
    async def test_failed_send_is_retried_next_tick(self) -> None:
        store = _DownStore(run=_run(_S.AWAITING_THESIS), topic=_topic())
        assert await _prompts(store).tick() == 0
        assert store.saved == []


_SP = timedelta(hours=-3)


def _sp(day: int, hour: int, minute: int = 0) -> datetime:
    """2026-10-20 is a Tuesday; times in São Paulo (UTC-3)."""
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC) - _SP


@pytest.mark.unit
class TestPovSlots:
    # Scenario Outline: Next POV slot
    @pytest.mark.parametrize(
        ("now", "slot"),
        [
            (_sp(20, 11, 30), _sp(20, 12)),
            (_sp(20, 11, 50), _sp(22, 12)),
            (_sp(22, 12), _sp(27, 12)),
            (_sp(24, 9), _sp(27, 12)),
        ],
        ids=["tue-early", "tue-too-late", "thu-at-noon", "saturday"],
    )
    def test_next_slot(self, now: datetime, slot: datetime) -> None:
        assert PovPublishSlots().next_slot(now) == slot

    def test_policy_for_mode(self) -> None:
        assert isinstance(slot_policy_for("pov"), PovPublishSlots)
        assert slot_policy_for("news_analysis") is None
        assert slot_policy_for(None) is None

    def test_week_bounds(self) -> None:
        start, end = sao_paulo_week(_sp(22, 23, 59))
        assert start == _sp(19, 0)
        assert end == _sp(26, 0)
        assert sao_paulo_week(_sp(19, 0))[0] == start
