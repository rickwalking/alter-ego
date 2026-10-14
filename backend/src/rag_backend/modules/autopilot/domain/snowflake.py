"""Twitter snowflake timestamps.

A status id encodes milliseconds since the Twitter epoch in the high bits.
The lower 22 bits are worker and sequence data and are ignored.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from rag_backend.modules.autopilot.constants import TWITTER_SNOWFLAKE_EPOCH_MS

_MS_PER_SECOND = 1000
_WORKER_SHIFT = 22


def posted_at_from_snowflake(status_id: int) -> datetime:
    """UTC instant encoded in a status id. Exact to the millisecond."""
    millis = (status_id >> _WORKER_SHIFT) + TWITTER_SNOWFLAKE_EPOCH_MS
    seconds, remainder = divmod(millis, _MS_PER_SECOND)
    moment = datetime.fromtimestamp(seconds, tz=UTC)
    return moment + timedelta(milliseconds=remainder)
