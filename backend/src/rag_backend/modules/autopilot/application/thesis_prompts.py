"""Ask the owner to confirm a POV run's thesis on Telegram (AE-0377).

Runs on the worker's Telegram tick, after the runner moved a POV run to
``awaiting_thesis``. The prompt is sent once per run: the run's notice ledger
records it, so a replayed tick never asks twice. A failed send is logged and
retried on the next tick (the run waits; it expires after 72 hours).
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from rag_backend.modules.autopilot.domain.exceptions import TelegramDeliveryError
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import record_status
from rag_backend.modules.autopilot.domain.notify import SaveNoticeLog, StatusNotice
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotRunRepository,
    NoticeLogStore,
    Notifier,
    TopicCandidateRepository,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.thesis import (
    thesis_keyboard,
    thesis_notice_key,
    thesis_prompt_text,
)
from rag_backend.modules.autopilot.pov_constants import LOG_THESIS

logger = structlog.get_logger()

THESIS_SCAN_LIMIT = 10
LOG_PROMPT_SENT = "prompt_sent"
LOG_PROMPT_FAILED = "prompt_failed"


@dataclass(frozen=True, kw_only=True)
class ThesisPromptDependencies:
    """Ports for one Telegram tick."""

    runs: AutopilotRunRepository
    topics: TopicCandidateRepository
    notices: NoticeLogStore
    notifier: Notifier
    chat_id: str
    configured: bool


class ThesisPromptService:
    """Send each ``awaiting_thesis`` run's prompt exactly once."""

    def __init__(self, deps: ThesisPromptDependencies) -> None:
        self._deps = deps

    async def tick(self) -> int:
        """Prompt the runs still waiting for one. Returns how many were sent."""
        if not self._deps.configured:
            return 0
        query = RunListQuery(
            state=AutopilotRunState.AWAITING_THESIS, limit=THESIS_SCAN_LIMIT
        )
        sent = 0
        for run in await self._deps.runs.list_by_state(query):
            sent += await self._prompt(run)
        return sent

    async def _prompt(self, run: AutopilotRun) -> int:
        key = thesis_notice_key(run.run_id)
        if key in run.notice_log.statuses:
            return 0
        topic = await self._deps.topics.get_topic(run.topic_candidate_id)
        if topic is None:
            return 0
        try:
            result = await self._deps.notifier.send_status(
                StatusNotice(
                    chat_id=self._deps.chat_id,
                    run_id=run.run_id,
                    text=thesis_prompt_text(topic),
                    keyboard=thesis_keyboard(run.run_id),
                )
            )
        except TelegramDeliveryError as exc:
            logger.warning(
                LOG_THESIS,
                run_id=str(run.run_id),
                outcome=LOG_PROMPT_FAILED,
                error=str(exc),
            )
            return 0
        log = record_status(run.notice_log, key, result.message_id)
        await self._deps.notices.save(SaveNoticeLog(run_id=run.run_id, log=log))
        logger.info(LOG_THESIS, run_id=str(run.run_id), outcome=LOG_PROMPT_SENT)
        return 1


__all__ = ["ThesisPromptDependencies", "ThesisPromptService"]
