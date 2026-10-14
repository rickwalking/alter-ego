"""Snowflake timestamp round-trip (AE-0352).

Gherkin: tests/features/autopilot_signals.feature
The X scenario depends on this pure function for the 48 hour cutoff.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st

from rag_backend.modules.autopilot.constants import TWITTER_SNOWFLAKE_EPOCH_MS
from rag_backend.modules.autopilot.domain.snowflake import posted_at_from_snowflake

_MS_PER_SECOND = 1000
_FIFTY_YEARS_MS = 50 * 365 * 24 * 60 * 60 * _MS_PER_SECOND
_WORKER_BITS = (1 << 22) - 1


def _moment(millis: int) -> datetime:
    seconds, remainder = divmod(millis, _MS_PER_SECOND)
    return datetime.fromtimestamp(seconds, tz=UTC) + timedelta(milliseconds=remainder)


@given(
    millis=st.integers(
        min_value=TWITTER_SNOWFLAKE_EPOCH_MS,
        max_value=TWITTER_SNOWFLAKE_EPOCH_MS + _FIFTY_YEARS_MS,
    ),
    worker=st.integers(min_value=0, max_value=_WORKER_BITS),
)
@hypothesis_settings(max_examples=40)
def test_snowflake_round_trip_ignores_worker_bits(millis: int, worker: int) -> None:
    """Encoding a timestamp and any 22 worker bits decodes to that timestamp."""
    status_id = ((millis - TWITTER_SNOWFLAKE_EPOCH_MS) << 22) | worker
    assert posted_at_from_snowflake(status_id) == _moment(millis)


def test_one_second_after_the_twitter_epoch() -> None:
    """A fixed id one second after the epoch decodes to that instant."""
    status_id = _MS_PER_SECOND << 22
    expected = _moment(TWITTER_SNOWFLAKE_EPOCH_MS + _MS_PER_SECOND)
    assert posted_at_from_snowflake(status_id) == expected
