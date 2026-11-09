"""The thesis prompt reaches a new run when older prompted runs still wait.

Gherkin: tests/features/autopilot_pov_thesis.feature
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import UUID, uuid4

import pytest

from rag_backend.modules.autopilot.application.thesis_prompts import (
    ThesisPromptDependencies,
    ThesisPromptService,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    AutopilotRunState,
    TopicCandidate,
)
from rag_backend.modules.autopilot.domain.notice_log import record_status
from rag_backend.modules.autopilot.domain.notify import (
    SaveNoticeLog,
    StatusNotice,
    StatusSendResult,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.thesis import thesis_notice_key

_WAITING = AutopilotRunState.AWAITING_THESIS
_ALREADY_ASKED = 10


def _run(*, asked: bool) -> AutopilotRun:
    run = AutopilotRun(
        run_id=uuid4(),
        topic_candidate_id=uuid4(),
        carousel_project_id=None,
        state=_WAITING,
        state_reason=None,
        publish_attempts=0,
        telegram_message_ids=(),
        ig_container_id=None,
        ig_post_id=None,
        ig_permalink=None,
    )
    if not asked:
        return run
    log = record_status(run.notice_log, thesis_notice_key(run.run_id), 1)
    return replace(run, notice_log=log)


def _topic(candidate_id: UUID) -> TopicCandidate:
    return TopicCandidate(
        candidate_id=candidate_id,
        title="A Nvidia investiga o CEO",
        angle="a",
        why_viral="w",
        audience="developers",
        niche="AI",
        brief="b",
        sources=("https://example.com/n",),
        score=80,
        signal_hash="h",
        status="generate_now",
        content_mode="pov_news",
        thesis_draft="Uma tese.",
    )


@dataclass
class _OldestFirstStore:
    """Honors ``limit`` like the SQL repository: oldest ``updated_at`` first."""

    runs: list[AutopilotRun]
    sent: list[StatusNotice] = field(default_factory=list)

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        matching = [run for run in self.runs if run.state is query.state]
        return matching[: query.limit]

    async def get_topic(self, candidate_id: UUID) -> TopicCandidate | None:
        return _topic(candidate_id)

    async def save(self, command: SaveNoticeLog) -> None:
        self.runs = [
            replace(run, notice_log=command.log)
            if run.run_id == command.run_id
            else run
            for run in self.runs
        ]

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        self.sent.append(notice)
        return StatusSendResult(message_id=len(self.sent) + 100)


def _service(store: _OldestFirstStore) -> ThesisPromptService:
    return ThesisPromptService(
        ThesisPromptDependencies(
            runs=store,
            topics=store,
            notices=store,
            notifier=store,
            chat_id="42",
            configured=True,
        )
    )


@pytest.mark.unit
class TestThesisPromptScan:
    # Scenario: A new run is asked even when older runs still wait
    @pytest.mark.asyncio
    async def test_new_run_behind_prompted_runs_is_asked(self) -> None:
        older = [_run(asked=True) for _ in range(_ALREADY_ASKED)]
        newer = _run(asked=False)
        store = _OldestFirstStore(runs=[*older, newer])

        assert await _service(store).tick() == 1

        assert len(store.sent) == 1
        assert store.sent[0].run_id == newer.run_id
        assert "A Nvidia investiga o CEO" in store.sent[0].text
        assert await _service(store).tick() == 0
