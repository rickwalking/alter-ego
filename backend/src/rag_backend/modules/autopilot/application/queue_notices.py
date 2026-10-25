"""Telegram-tick notices of the queue flow: "Aprovar todas" summary, backlog notes.

* When two or more POV runs whose prompts went out still wait for their thesis,
  Pedro gets one summary listing them with "Aprovar todas". Each listed run's
  notice ledger records it, so the summary is not sent again for the same runs.
* Themes that just joined the backlog are announced once, each with a
  "Gerar agora" button; themes older than 7 days leave the backlog with one note.

Every message is sent first and recorded after, so a failed send is retried on
the next tick; a failed send never rolls back the rest of the tick.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import structlog

from rag_backend.modules.autopilot.domain.backlog import (
    BacklogChange,
    BacklogStore,
    BacklogTheme,
    BacklogWindow,
    expiry_cutoff,
)
from rag_backend.modules.autopilot.domain.exceptions import TelegramDeliveryError
from rag_backend.modules.autopilot.domain.messages import InlineButton, InlineKeyboard
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import record_status
from rag_backend.modules.autopilot.domain.notify import SaveNoticeLog, StatusNotice
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    Clock,
    NoticeLogStore,
    Notifier,
    TopicCandidateRepository,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.queue_position import joined_titles
from rag_backend.modules.autopilot.domain.thesis import thesis_notice_key
from rag_backend.modules.autopilot.queue_constants import (
    APPROVE_ALL_LIMIT,
    BACKLOG_WAITING,
    BUTTON_APPROVE_ALL,
    BUTTON_GENERATE_NOW,
    BUTTON_TITLE_MAX_CHARS,
    CALLBACK_APPROVE_ALL,
    CALLBACK_GENERATE_NOW_PREFIX,
    CANDIDATE_BACKLOG,
    CANDIDATE_BACKLOG_EXPIRED,
    CANDIDATE_BACKLOG_NOTED,
    ELLIPSIS,
    LOG_QUEUE_FLOW,
    TEXT_BACKLOG_EXPIRED,
    TEXT_BACKLOG_NEW,
    TEXT_BATCH_HEADER,
    TEXT_BATCH_LINE,
    TEXT_BATCH_NO_DRAFT,
    THESIS_BATCH_MIN,
    THESIS_BATCH_NOTICE_KEY,
)

logger = structlog.get_logger()

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
OUTCOME_SEND_FAILED = "send_failed"


@dataclass(frozen=True, kw_only=True)
class QueueNoticeDependencies:
    """Ports for one Telegram tick."""

    runs: AutopilotRunRepository
    topics: TopicCandidateRepository
    notices: NoticeLogStore
    notifier: Notifier
    backlog: BacklogStore
    clock: Clock
    chat_id: str
    configured: bool


class QueueNoticeService:
    """Send the approve-all summary and the backlog notes, each once."""

    def __init__(self, deps: QueueNoticeDependencies) -> None:
        self._deps = deps

    async def tick(self) -> int:
        """Returns how many messages were sent."""
        if not self._deps.configured:
            return 0
        sent = await self._thesis_batch()
        sent += await self._new_backlog()
        return sent + await self._expired_backlog()

    async def _thesis_batch(self) -> int:
        query = RunListQuery(
            state=AutopilotRunState.AWAITING_THESIS, limit=APPROVE_ALL_LIMIT
        )
        runs = [
            run
            for run in await self._deps.runs.list_by_state(query)
            if thesis_notice_key(run.run_id) in run.notice_log.statuses
        ]
        if len(runs) < THESIS_BATCH_MIN or all(_batched(run) for run in runs):
            return 0
        lines = [
            await self._batch_line(index, run) for index, run in enumerate(runs, 1)
        ]
        text = "\n".join((TEXT_BATCH_HEADER.format(count=len(runs)), *lines))
        keyboard = InlineKeyboard(
            rows=(
                (
                    InlineButton(
                        text=BUTTON_APPROVE_ALL, callback_data=CALLBACK_APPROVE_ALL
                    ),
                ),
            )
        )
        message_id = await self._send(
            StatusNotice(
                chat_id=self._deps.chat_id,
                run_id=runs[0].run_id,
                text=text,
                keyboard=keyboard,
            )
        )
        if message_id is None:
            return 0
        for run in runs:
            log = record_status(run.notice_log, THESIS_BATCH_NOTICE_KEY, message_id)
            await self._deps.notices.save(SaveNoticeLog(run_id=run.run_id, log=log))
        return 1

    async def _batch_line(self, index: int, run: AutopilotRun) -> str:
        topic = await self._deps.topics.get_topic(run.topic_candidate_id)
        if topic is None or not topic.thesis_draft:
            title = topic.title if topic is not None else ""
            return TEXT_BATCH_NO_DRAFT.format(index=index, title=title)
        return TEXT_BATCH_LINE.format(index=index, thesis=topic.thesis_draft)

    async def _new_backlog(self) -> int:
        themes = await self._deps.backlog.unannounced()
        if not themes:
            return 0
        rows = tuple((_generate_now_button(theme),) for theme in themes)
        message_id = await self._send(
            StatusNotice(
                chat_id=self._deps.chat_id,
                run_id=themes[0].candidate_id,
                text=TEXT_BACKLOG_NEW.format(count=len(themes)),
                keyboard=InlineKeyboard(rows=rows),
            )
        )
        if message_id is None:
            return 0
        await self._mark(themes, CANDIDATE_BACKLOG_NOTED, (CANDIDATE_BACKLOG,))
        return 1

    async def _expired_backlog(self) -> int:
        cutoff = expiry_cutoff(self._deps.clock.now())
        themes = await self._deps.backlog.waiting(
            BacklogWindow(since=_EPOCH, before=cutoff)
        )
        if not themes:
            return 0
        titles = joined_titles(theme.title for theme in themes)
        message_id = await self._send(
            StatusNotice(
                chat_id=self._deps.chat_id,
                run_id=themes[0].candidate_id,
                text=TEXT_BACKLOG_EXPIRED.format(titles=titles),
                keyboard=None,
            )
        )
        if message_id is None:
            return 0
        await self._mark(themes, CANDIDATE_BACKLOG_EXPIRED, BACKLOG_WAITING)
        return 1

    async def _mark(
        self, themes: list[BacklogTheme], status: str, expected: tuple[str, ...]
    ) -> None:
        ids = tuple(theme.candidate_id for theme in themes)
        await self._deps.backlog.change(
            BacklogChange(candidate_ids=ids, status=status, expected=expected)
        )

    async def _send(self, notice: StatusNotice) -> int | None:
        try:
            result = await self._deps.notifier.send_status(notice)
        except TelegramDeliveryError as exc:
            logger.warning(LOG_QUEUE_FLOW, outcome=OUTCOME_SEND_FAILED, error=str(exc))
            return None
        return result.message_id


def _batched(run: AutopilotRun) -> bool:
    return THESIS_BATCH_NOTICE_KEY in run.notice_log.statuses


def _generate_now_button(theme: BacklogTheme) -> InlineButton:
    title = theme.title
    if len(title) > BUTTON_TITLE_MAX_CHARS:
        title = title[: BUTTON_TITLE_MAX_CHARS - 1] + ELLIPSIS
    return InlineButton(
        text=BUTTON_GENERATE_NOW.format(title=title),
        callback_data=f"{CALLBACK_GENERATE_NOW_PREFIX}{theme.candidate_id}",
    )


__all__ = ["QueueNoticeDependencies", "QueueNoticeService"]
