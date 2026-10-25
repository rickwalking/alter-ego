"""The "Aprovar todas" summary and the backlog notes on the Telegram tick.

Feature: backend/tests/features/telegram_queue_flow_ae0523.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from rag_backend.modules.autopilot.application.queue_notices import (
    QueueNoticeDependencies,
    QueueNoticeService,
)
from rag_backend.modules.autopilot.domain.backlog import (
    BacklogChange,
    BacklogTheme,
    BacklogWindow,
    GenerateNowCommand,
)
from rag_backend.modules.autopilot.domain.exceptions import TelegramDeliveryError
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
)
from rag_backend.modules.autopilot.domain.notice_log import NoticeLog
from rag_backend.modules.autopilot.domain.notify import (
    ReviewNotice,
    ReviewSendResult,
    SaveNoticeLog,
    StatusNotice,
    StatusSendResult,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.thesis import thesis_notice_key
from rag_backend.modules.autopilot.queue_constants import (
    CALLBACK_APPROVE_ALL,
    CANDIDATE_BACKLOG,
    CANDIDATE_BACKLOG_EXPIRED,
    CANDIDATE_BACKLOG_NOTED,
)

_NOW = datetime(2026, 10, 24, 14, 0, tzinfo=UTC)
_S = AutopilotRunState


class _Clock:
    def now(self) -> datetime:
        return _NOW


@dataclass
class _Runs:
    runs: dict[UUID, AutopilotRun] = field(default_factory=dict)

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        return [run for run in self.runs.values() if run.state is query.state]

    async def get_topic(self, candidate_id: UUID) -> TopicCandidate | None:
        return _TOPICS.get(candidate_id)

    async def add_topic(self, candidate: TopicCandidate) -> None:
        _TOPICS[candidate.candidate_id] = candidate

    async def save(self, command: SaveNoticeLog) -> None:
        run = self.runs[command.run_id]
        self.runs[command.run_id] = replace(run, notice_log=command.log)


_TOPICS: dict[UUID, TopicCandidate] = {}


@dataclass
class _Notifier:
    sent: list[StatusNotice] = field(default_factory=list)
    fail: bool = False

    async def send_review(self, notice: ReviewNotice) -> ReviewSendResult:
        raise AssertionError(notice)

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        if self.fail:
            raise TelegramDeliveryError("down")
        self.sent.append(notice)
        return StatusSendResult(message_id=100 + len(self.sent))


@dataclass
class _Backlog:
    themes: dict[UUID, tuple[BacklogTheme, str]] = field(default_factory=dict)

    async def waiting(self, window: BacklogWindow) -> list[BacklogTheme]:
        return [
            theme
            for theme, status in self.themes.values()
            if status in (CANDIDATE_BACKLOG, CANDIDATE_BACKLOG_NOTED)
            and window.since <= theme.created_at < window.before
        ]

    async def change(self, change: BacklogChange) -> tuple[UUID, ...]:
        moved: list[UUID] = []
        for candidate_id in change.candidate_ids:
            theme, status = self.themes[candidate_id]
            if status in change.expected:
                self.themes[candidate_id] = (theme, change.status)
                moved.append(candidate_id)
        return tuple(moved)

    async def unannounced(self) -> list[BacklogTheme]:
        return [t for t, status in self.themes.values() if status == CANDIDATE_BACKLOG]

    async def generate_now(self, command: GenerateNowCommand) -> BacklogTheme | None:
        raise AssertionError(command)


def _prompted_run(title: str, draft: str | None) -> AutopilotRun:
    topic_id = uuid4()
    _TOPICS[topic_id] = TopicCandidate(
        candidate_id=topic_id,
        title=title,
        angle="a",
        why_viral="w",
        audience="dev",
        niche="AI",
        brief="b",
        sources=("https://example.com/a",),
        score=80,
        signal_hash=title,
        status="accepted",
        content_mode="pov",
        thesis_draft=draft,
    )
    run_id = uuid4()
    return AutopilotRun(
        run_id=run_id,
        topic_candidate_id=topic_id,
        carousel_project_id=None,
        state=_S.AWAITING_THESIS,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
        notice_log=NoticeLog(statuses=(thesis_notice_key(run_id),)),
    )


def _theme(title: str, age: timedelta, status: str) -> tuple[BacklogTheme, str]:
    theme = BacklogTheme(candidate_id=uuid4(), title=title, created_at=_NOW - age)
    return theme, status


def _service(runs: _Runs, backlog: _Backlog, notifier: _Notifier) -> QueueNoticeService:
    return QueueNoticeService(
        QueueNoticeDependencies(
            runs=runs,
            topics=runs,
            notices=runs,
            notifier=notifier,
            backlog=backlog,
            clock=_Clock(),
            chat_id="42",
            configured=True,
        )
    )


@pytest.mark.asyncio
async def test_several_waiting_theses_get_one_approve_all_message() -> None:
    """Scenario: Several waiting theses get one "Aprovar todas" message"""
    first = _prompted_run("Agentes", "Tese um")
    second = _prompted_run("Sem rascunho", None)
    runs = _Runs(runs={first.run_id: first, second.run_id: second})
    notifier = _Notifier()
    service = _service(runs, _Backlog(), notifier)
    assert await service.tick() == 1
    assert await service.tick() == 0
    assert len(notifier.sent) == 1
    summary = notifier.sent[0]
    assert summary.text.startswith("📋 2 teses esperando a sua confirmação:")
    assert "1. «Tese um»" in summary.text
    assert "2. Sem rascunho (sem tese: use Editar" in summary.text
    assert summary.keyboard is not None
    assert summary.keyboard.rows[0][0].callback_data == CALLBACK_APPROVE_ALL


@pytest.mark.asyncio
async def test_a_single_waiting_thesis_gets_no_summary() -> None:
    """Scenario: Several waiting theses get one "Aprovar todas" message"""
    only = _prompted_run("Solo", "Tese")
    notifier = _Notifier()
    service = _service(_Runs(runs={only.run_id: only}), _Backlog(), notifier)
    assert await service.tick() == 0
    assert notifier.sent == []


@pytest.mark.asyncio
async def test_new_backlog_themes_are_announced_once_with_generate_now() -> None:
    """Scenario: New backlog themes are announced once with "Gerar agora\""""
    backlog = _Backlog()
    for title in (
        "Primeiro tema",
        "Um título bem comprido que passa do limite do botão",
    ):
        theme = _theme(title, timedelta(hours=1), CANDIDATE_BACKLOG)
        backlog.themes[theme[0].candidate_id] = theme
    notifier = _Notifier()
    service = _service(_Runs(), backlog, notifier)
    assert await service.tick() == 1
    assert await service.tick() == 0
    note = notifier.sent[0]
    assert note.text.startswith("🕗 2 tema(s) passaram do limite diário")
    assert note.keyboard is not None
    buttons = [row[0] for row in note.keyboard.rows]
    assert buttons[0].text == "⚡ Gerar agora: Primeiro tema"
    assert buttons[1].text.endswith("…")
    assert all(b.callback_data.startswith("ap:qnow:") for b in buttons)
    assert all(len(b.callback_data.encode()) <= 64 for b in buttons)
    assert {s for _, s in backlog.themes.values()} == {CANDIDATE_BACKLOG_NOTED}


@pytest.mark.asyncio
async def test_a_backlog_theme_expires_after_seven_days_with_one_note() -> None:
    """Scenario: A backlog theme expires after 7 days with one note"""
    old = _theme("Velho", timedelta(days=8), CANDIDATE_BACKLOG_NOTED)
    fresh = _theme("Novo", timedelta(days=1), CANDIDATE_BACKLOG_NOTED)
    backlog = _Backlog(themes={old[0].candidate_id: old, fresh[0].candidate_id: fresh})
    notifier = _Notifier()
    service = _service(_Runs(), backlog, notifier)
    assert await service.tick() == 1
    assert await service.tick() == 0
    assert [n.text for n in notifier.sent] == [
        "⌛ Saíram da fila de espera depois de 7 dias: Velho"
    ]
    assert backlog.themes[old[0].candidate_id][1] == CANDIDATE_BACKLOG_EXPIRED
    assert backlog.themes[fresh[0].candidate_id][1] == CANDIDATE_BACKLOG_NOTED


@pytest.mark.asyncio
async def test_a_failed_send_is_retried_on_the_next_tick() -> None:
    """Scenario: New backlog themes are announced once with "Gerar agora\""""
    theme = _theme("Tema", timedelta(hours=1), CANDIDATE_BACKLOG)
    backlog = _Backlog(themes={theme[0].candidate_id: theme})
    notifier = _Notifier(fail=True)
    service = _service(_Runs(), backlog, notifier)
    assert await service.tick() == 0
    assert backlog.themes[theme[0].candidate_id][1] == CANDIDATE_BACKLOG
    notifier.fail = False
    assert await service.tick() == 1
