"""Publish-time rules for the owner's schedule (AE-0370). Pure, no I/O.

Every time is computed in America/Sao_Paulo and returned in UTC, so the
server's own zone never matters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.schedule_constants import (
    DATE_TIME_PATTERN,
    ERR_TIME_FORMAT,
    ERR_TIME_PAST,
    ERR_TIME_TOO_FAR,
    LABEL_TODAY,
    LABEL_TOMORROW,
    LOCAL_LABEL_FORMAT,
    LOCAL_TIME_FORMAT,
    REASON_SCHEDULE_DUE,
    SCHEDULE_LATE_NOTICE_MINUTES,
    SCHEDULE_MAX_AHEAD_DAYS,
    SCHEDULE_MIN_LEAD_MINUTES,
    SCHEDULE_SLOT_COUNT,
    SCHEDULE_SLOTS,
    SCHEDULE_TIMEZONE,
    SECONDS_PER_MINUTE,
    TIME_PATTERN,
    TIME_SEPARATOR,
)

_TIME = re.compile(TIME_PATTERN)
_DATE_TIME = re.compile(DATE_TIME_PATTERN)


@dataclass(frozen=True, kw_only=True)
class TimeChoice:
    """A parsed owner time in UTC, or the error code that rejected it."""

    at: datetime | None
    error: str | None


@dataclass(frozen=True, kw_only=True)
class _DateParts:
    year: int
    month: int
    day: int


def schedule_zone() -> ZoneInfo:
    """The owner's zone."""
    return ZoneInfo(SCHEDULE_TIMEZONE)


def next_slots(now: datetime) -> tuple[datetime, ...]:
    """The next three slots at least 15 minutes ahead, rolling over to tomorrow."""
    earliest = now + timedelta(minutes=SCHEDULE_MIN_LEAD_MINUTES)
    today = now.astimezone(schedule_zone()).date()
    found: list[datetime] = []
    offset = 0
    while len(found) < SCHEDULE_SLOT_COUNT:
        day = today + timedelta(days=offset)
        found.extend(slot for slot in _slots_on(day) if slot >= earliest)
        offset += 1
    return tuple(found[:SCHEDULE_SLOT_COUNT])


def check_choice(at: datetime, now: datetime) -> str | None:
    """Why ``at`` cannot be scheduled (past, or over 30 days ahead), or None."""
    if at <= now:
        return ERR_TIME_PAST
    if at - now > timedelta(days=SCHEDULE_MAX_AHEAD_DAYS):
        return ERR_TIME_TOO_FAR
    return None


def parse_owner_time(text: str, now: datetime) -> TimeChoice:
    """``HH:MM`` (today, else tomorrow) or ``DD/MM HH:MM``, owner local time."""
    cleaned = text.strip()
    clock = _TIME.fullmatch(cleaned)
    if clock is not None:
        return _from_clock(clock, now)
    dated = _DATE_TIME.fullmatch(cleaned)
    if dated is None:
        return TimeChoice(at=None, error=ERR_TIME_FORMAT)
    return _from_date(dated, now)


def local_label(at: datetime) -> str:
    """``dd/mm HH:MM`` in the owner's zone."""
    return at.astimezone(schedule_zone()).strftime(LOCAL_LABEL_FORMAT)


def slot_label(at: datetime, now: datetime) -> str:
    """``hoje 18:00``, ``amanhã 12:00``, or ``dd/mm HH:MM`` further out."""
    zone = schedule_zone()
    local = at.astimezone(zone)
    days = (local.date() - now.astimezone(zone).date()).days
    clock = local.strftime(LOCAL_TIME_FORMAT)
    if days == 0:
        return LABEL_TODAY.format(time=clock)
    if days == 1:
        return LABEL_TOMORROW.format(time=clock)
    return local_label(at)


def late_minutes(scheduled_at: datetime | None, now: datetime) -> int | None:
    """Minutes past the schedule when over the notice threshold, else None."""
    if scheduled_at is None:
        return None
    late = int((now - scheduled_at).total_seconds() // SECONDS_PER_MINUTE)
    if late <= SCHEDULE_LATE_NOTICE_MINUTES:
        return None
    return late


def epoch_of(at: datetime) -> int:
    """Unix seconds, for a slot's callback data."""
    return int(at.timestamp())


def from_epoch(epoch: int) -> datetime:
    """The UTC moment a slot button carries."""
    return datetime.fromtimestamp(epoch, tz=UTC)


def clears_schedule(command: TransitionCommand) -> bool:
    """Leaving ``scheduled`` other than by the due tick drops ``scheduled_at``.

    The due tick keeps it, so the published notice can say how late it was.
    """
    if command.expected is not AutopilotRunState.SCHEDULED:
        return False
    return command.reason != REASON_SCHEDULE_DUE


def _slots_on(day: date) -> list[datetime]:
    return [_utc(day, _slot_time(slot)) for slot in SCHEDULE_SLOTS]


def _slot_time(slot: str) -> time:
    hour, minute = slot.split(TIME_SEPARATOR)
    return time(int(hour), int(minute))


def _utc(day: date, clock: time) -> datetime:
    return datetime.combine(day, clock, tzinfo=schedule_zone()).astimezone(UTC)


def _from_clock(match: re.Match[str], now: datetime) -> TimeChoice:
    clock = _clock(match.group(1), match.group(2))
    if clock is None:
        return TimeChoice(at=None, error=ERR_TIME_FORMAT)
    today = now.astimezone(schedule_zone()).date()
    at = _utc(today, clock)
    if at <= now:
        at = _utc(today + timedelta(days=1), clock)
    return TimeChoice(at=at, error=None)


def _from_date(match: re.Match[str], now: datetime) -> TimeChoice:
    clock = _clock(match.group(3), match.group(4))
    year = now.astimezone(schedule_zone()).year
    parts = _DateParts(year=year, month=int(match.group(2)), day=int(match.group(1)))
    day = _day(parts)
    if clock is None or day is None:
        return TimeChoice(at=None, error=ERR_TIME_FORMAT)
    at = _utc(day, clock)
    if at <= now:
        at = _next_year(parts, clock, now) or at
    error = check_choice(at, now)
    return TimeChoice(at=None if error else at, error=error)


def _next_year(parts: _DateParts, clock: time, now: datetime) -> datetime | None:
    """On 30/12, ``02/01`` means next January when that is within 30 days."""
    day = _day(_DateParts(year=parts.year + 1, month=parts.month, day=parts.day))
    if day is None:
        return None
    later = _utc(day, clock)
    if check_choice(later, now) is not None:
        return None
    return later


def _day(parts: _DateParts) -> date | None:
    try:
        return date(parts.year, parts.month, parts.day)
    except ValueError:
        return None


def _clock(hour: str, minute: str) -> time | None:
    try:
        return time(int(hour), int(minute))
    except ValueError:
        return None
