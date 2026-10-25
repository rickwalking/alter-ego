"""Deliver ``content.autopilot.*`` notices and the 24 hour reminder.

The worker tick calls ``tick``. The outbox relay only publishes to Redis;
nothing else consumes this event family, so this service reads the outbox
rows directly and skips a notice the run's ledger already records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog

from rag_backend.modules.autopilot.constants import (
    PAYLOAD_PROJECT_ID,
)
from rag_backend.modules.autopilot.domain.carousel_defaults import profile_line
from rag_backend.modules.autopilot.domain.dead_letter import status_body
from rag_backend.modules.autopilot.domain.escalation_detail import detail_of
from rag_backend.modules.autopilot.domain.exceptions import (
    NotifierUnconfiguredError,
    TelegramDeliveryError,
    TelegramRateLimitedError,
)
from rag_backend.modules.autopilot.domain.messages import (
    StatusCopy,
    days_remaining_of,
    notice_kind,
    owner_ui_link,
    permalink_of,
    persona_score_of,
    reason_of,
    review_keyboard,
    revision_of,
    sources_count_of,
    status_text,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRun, AutopilotRunState
from rag_backend.modules.autopilot.domain.notice_log import (
    NoticeLog,
    ReviewRecord,
    attempt_count,
    bump_attempt,
    find_review,
    is_review_complete,
    record_reminder,
    record_review,
    record_status,
    reminder_revision,
)
from rag_backend.modules.autopilot.domain.notify import (
    AutopilotOutboxEvent,
    ReviewFacts,
    ReviewNotice,
    SaveNoticeLog,
    StatusNotice,
)
from rag_backend.modules.autopilot.domain.ports import (
    AutopilotEventSource,
    AutopilotRunRepository,
    Clock,
    NoticeLogStore,
    Notifier,
    ReviewFactsSource,
)
from rag_backend.modules.autopilot.domain.publish import RunListQuery
from rag_backend.modules.autopilot.domain.published_copy import post_extras_of
from rag_backend.modules.autopilot.domain.status_keyboard import status_keyboard
from rag_backend.modules.autopilot.notify_constants import (
    ATTEMPT_REMINDER_PREFIX,
    ATTEMPT_REVIEW_PREFIX,
    ATTEMPT_STATUS_PREFIX,
    KIND_REMINDER,
    KIND_REVIEW,
    LOG_NOTIFIER_DROPPED,
    LOG_NOTIFIER_FAILED,
    LOG_NOTIFIER_UNCONFIGURED,
    NOTIFY_BATCH,
    NOTIFY_MAX_ATTEMPTS,
    REMINDER_AFTER_HOURS,
    REMINDER_SCAN_LIMIT,
)

logger = structlog.get_logger()


@dataclass(frozen=True, kw_only=True)
class NotificationDependencies:
    """Ports for one worker tick."""

    events: AutopilotEventSource
    runs: AutopilotRunRepository
    facts: ReviewFactsSource
    notices: NoticeLogStore
    notifier: Notifier
    clock: Clock
    chat_id: str
    configured: bool
    web_base_url: str


@dataclass(frozen=True, kw_only=True)
class _ReviewJob:
    event: AutopilotOutboxEvent
    run: AutopilotRun
    log: NoticeLog
    key: str
    revision: int
    facts: ReviewFacts


@dataclass(frozen=True, kw_only=True)
class _StatusJob:
    event: AutopilotOutboxEvent
    run: AutopilotRun
    kind: str


@dataclass(frozen=True, kw_only=True)
class _Failure:
    run: AutopilotRun
    log: NoticeLog
    key: str
    detail: str


@dataclass(frozen=True, kw_only=True)
class _ReminderJob:
    run: AutopilotRun
    now: datetime


class OwnerNotificationService:
    """Send at most a small batch of notices, then due reminders."""

    def __init__(self, deps: NotificationDependencies) -> None:
        self._deps = deps

    async def tick(self) -> int:
        """Deliver pending notices. Returns how many Telegram calls succeeded."""
        if not _configured(self._deps):
            logger.info(LOG_NOTIFIER_UNCONFIGURED)
            return 0
        sent = await self._deliver()
        room = NOTIFY_BATCH - sent
        if room <= 0:
            return sent
        return sent + await self._remind(room)

    async def _deliver(self) -> int:
        """Oldest first. The cursor moves only over a settled prefix (QA r1)."""
        sent = 0
        blocked = False
        for event in await self._deps.events.recent():
            if sent >= NOTIFY_BATCH:
                return sent
            if await self._one(event):
                sent += 1
            blocked = blocked or not await self._settled(event)
            if not blocked:
                await self._deps.events.advance(event)
        return sent

    async def _settled(self, event: AutopilotOutboxEvent) -> bool:
        """True when this event needs no further delivery attempt."""
        kind = notice_kind(event.event_type, event.payload)
        run = await self._deps.runs.get(event.run_id)
        if kind is None or run is None:
            return True
        log = run.notice_log
        if kind == KIND_REVIEW:
            revision = revision_of(event.payload)
            key = f"{ATTEMPT_REVIEW_PREFIX}{revision}"
            return is_review_complete(log, revision) or _exhausted(log, key)
        key = f"{ATTEMPT_STATUS_PREFIX}{event.event_id}"
        return event.event_id in log.statuses or _exhausted(log, key)

    async def _one(self, event: AutopilotOutboxEvent) -> bool:
        kind = notice_kind(event.event_type, event.payload)
        if kind is None:
            return False
        run = await self._deps.runs.get(event.run_id)
        if run is None:
            return False
        if kind == KIND_REVIEW:
            return await self._review(event, run)
        return await self._status(event, run, kind)

    async def _review(self, event: AutopilotOutboxEvent, run: AutopilotRun) -> bool:
        revision = revision_of(event.payload)
        log = run.notice_log
        key = f"{ATTEMPT_REVIEW_PREFIX}{revision}"
        if is_review_complete(log, revision) or _exhausted(log, key):
            return False
        facts = await self._facts(event, run)
        if facts is None:
            failure = _Failure(run=run, log=log, key=key, detail=PAYLOAD_PROJECT_ID)
            return await self._fail(failure)
        job = _ReviewJob(
            event=event,
            run=run,
            log=log,
            key=key,
            revision=revision,
            facts=facts,
        )
        return await self._send_review(job)

    async def _send_review(self, job: _ReviewJob) -> bool:
        prior = find_review(job.log, job.revision)
        try:
            notice = _review_notice(self._deps, job, prior)
            result = await self._deps.notifier.send_review(notice)
        except TelegramRateLimitedError:
            return False
        except NotifierUnconfiguredError:
            return False
        except TelegramDeliveryError as exc:
            failure = _Failure(run=job.run, log=job.log, key=job.key, detail=exc.detail)
            return await self._fail(failure)
        stored = ReviewRecord(
            revision=job.revision,
            album_ids=result.album_ids,
            keyboard_id=result.keyboard_id,
        )
        await self._save(job.run, record_review(job.log, stored))
        return True

    async def _status(
        self,
        event: AutopilotOutboxEvent,
        run: AutopilotRun,
        kind: str,
    ) -> bool:
        log = run.notice_log
        key = f"{ATTEMPT_STATUS_PREFIX}{event.event_id}"
        if event.event_id in log.statuses or _exhausted(log, key):
            return False
        notice = _status_notice(self._deps, _StatusJob(event=event, run=run, kind=kind))
        try:
            result = await self._deps.notifier.send_status(notice)
        except TelegramRateLimitedError:
            return False
        except NotifierUnconfiguredError:
            return False
        except TelegramDeliveryError as exc:
            failure = _Failure(run=run, log=log, key=key, detail=exc.detail)
            return await self._fail(failure)
        await self._save(run, record_status(log, event.event_id, result.message_id))
        return True

    async def _remind(self, room: int) -> int:
        query = RunListQuery(
            state=AutopilotRunState.AWAITING_OWNER,
            limit=REMINDER_SCAN_LIMIT,
        )
        sent = 0
        now = self._deps.clock.now()
        for run in await self._deps.runs.list_by_state(query):
            if sent >= room:
                return sent
            if await self._one_reminder(_ReminderJob(run=run, now=now)):
                sent += 1
        return sent

    async def _one_reminder(self, job: _ReminderJob) -> bool:
        revision = reminder_revision(job.run.notice_log)
        key = f"{ATTEMPT_REMINDER_PREFIX}{revision}"
        if not _reminder_due(job, revision, key):
            return False
        notice = StatusNotice(
            chat_id=self._deps.chat_id,
            run_id=job.run.run_id,
            text=status_text(KIND_REMINDER, _empty_copy()),
            keyboard=review_keyboard(job.run.run_id),
        )
        try:
            result = await self._deps.notifier.send_status(notice)
        except TelegramRateLimitedError:
            return False
        except NotifierUnconfiguredError:
            return False
        except TelegramDeliveryError as exc:
            failure = _Failure(
                run=job.run,
                log=job.run.notice_log,
                key=key,
                detail=exc.detail,
            )
            return await self._fail(failure)
        updated = record_reminder(job.run.notice_log, revision, result.message_id)
        await self._save(job.run, updated)
        return True

    async def _facts(
        self,
        event: AutopilotOutboxEvent,
        run: AutopilotRun,
    ) -> ReviewFacts | None:
        project_id = _project_id(event, run)
        if not project_id:
            return None
        return await self._deps.facts.load(project_id)

    async def _fail(self, failure: _Failure) -> bool:
        updated = bump_attempt(failure.log, failure.key)
        await self._save(failure.run, updated)
        logger.warning(
            LOG_NOTIFIER_FAILED,
            run_id=str(failure.run.run_id),
            detail=failure.detail,
        )
        if attempt_count(updated, failure.key) >= NOTIFY_MAX_ATTEMPTS:
            logger.warning(
                LOG_NOTIFIER_DROPPED,
                run_id=str(failure.run.run_id),
                notice=failure.key,
            )
        return False

    async def _save(self, run: AutopilotRun, log: NoticeLog) -> None:
        await self._deps.notices.save(SaveNoticeLog(run_id=run.run_id, log=log))


def _configured(deps: NotificationDependencies) -> bool:
    return deps.configured and bool(deps.chat_id.strip())


def _exhausted(log: NoticeLog, key: str) -> bool:
    return attempt_count(log, key) >= NOTIFY_MAX_ATTEMPTS


def _project_id(event: AutopilotOutboxEvent, run: AutopilotRun) -> str:
    raw = event.payload.get(PAYLOAD_PROJECT_ID)
    if isinstance(raw, str) and raw:
        return raw
    return run.carousel_project_id or ""


def _review_notice(
    deps: NotificationDependencies,
    job: _ReviewJob,
    prior: ReviewRecord | None,
) -> ReviewNotice:
    album = prior.album_ids if prior is not None else ()
    return ReviewNotice(
        chat_id=deps.chat_id,
        run_id=job.event.run_id,
        title=job.facts.title,
        persona_score=persona_score_of(job.event.payload),
        sources_count=sources_count_of(job.event.payload),
        caption=job.facts.caption,
        slide_paths=job.facts.slide_paths,
        prior_album_ids=album,
        profile=_profile(job.facts),
        issues=job.facts.issues,
        fixable=job.facts.fixable,
        cover=job.facts.cover,
    )


def _profile(facts: ReviewFacts) -> str:
    return profile_line(facts.audience, facts.niche, facts.image_style)


def _status_notice(deps: NotificationDependencies, job: _StatusJob) -> StatusNotice:
    return StatusNotice(
        chat_id=deps.chat_id,
        run_id=job.run.run_id,
        text=status_body(job.kind, _copy(deps.web_base_url, job.event, job.run)),
        keyboard=status_keyboard(job.kind, job.run.run_id, job.event.payload),
    )


def _copy(base_url: str, event: AutopilotOutboxEvent, run: AutopilotRun) -> StatusCopy:
    project_id = run.carousel_project_id or ""
    return StatusCopy(
        reason=reason_of(event.payload),
        link=owner_ui_link(base_url, project_id),
        permalink=permalink_of(event.payload),
        days_remaining=days_remaining_of(event.payload),
        extras=post_extras_of(event.payload),
        detail=detail_of(event.payload),
    )


def _empty_copy() -> StatusCopy:
    return StatusCopy(reason="", link="", permalink="", days_remaining=None)


def _reminder_due(job: _ReminderJob, revision: int, key: str) -> bool:
    log = job.run.notice_log
    if revision in log.reminders or _exhausted(log, key):
        return False
    if job.run.updated_at is None:
        return False
    return job.now >= job.run.updated_at + timedelta(hours=REMINDER_AFTER_HOURS)
