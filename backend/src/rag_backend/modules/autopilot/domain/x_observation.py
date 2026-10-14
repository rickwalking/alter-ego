"""Decide which browser observations become ``x_browser`` signals.

Pure: the caller supplies the clock. A bad URL or a stale snowflake
rejects that item only. Control characters are stripped before storage
so post text stays inert data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rag_backend.modules.autopilot.constants import (
    REASON_EMPTY_HANDLE,
    REASON_EMPTY_TEXT,
    REASON_HANDLE_MISMATCH,
    REASON_NOT_STATUS_URL,
    REASON_STALE_STATUS,
)
from rag_backend.modules.autopilot.domain.signals import SignalSource, ensure_utc
from rag_backend.modules.autopilot.domain.snowflake import posted_at_from_snowflake
from rag_backend.modules.autopilot.domain.topic_text import strip_controls
from rag_backend.modules.autopilot.domain.x_status import (
    XStatusTarget,
    is_recent_status,
    parse_status_url,
)


@dataclass(frozen=True, kw_only=True)
class ObservedPostInput:
    """One schema-valid post before stripping and the status-url check."""

    url: str
    handle: str
    text: str
    likes: int | None
    reposts: int | None
    replies: int | None
    views: int | None
    observed_at: datetime


@dataclass(frozen=True, kw_only=True)
class AcceptedObservation:
    """A post that will be stored and added to the topic allowlist."""

    url: str
    handle: str
    text: str
    likes: int | None
    reposts: int | None
    replies: int | None
    views: int | None
    observed_at: datetime
    posted_at: datetime
    source: SignalSource


@dataclass(frozen=True, kw_only=True)
class ObservationRejection:
    """One item the response lists under ``rejected``."""

    url: str
    reason: str


@dataclass(frozen=True, kw_only=True)
class ObservationPlan:
    """Accepted signals (last write wins per URL) and the rejections."""

    accepted: tuple[AcceptedObservation, ...]
    rejected: tuple[ObservationRejection, ...]


@dataclass(frozen=True, kw_only=True)
class _AcceptedParts:
    """Pieces ``_accepted`` needs. Keeps that function to one argument."""

    post: ObservedPostInput
    target: XStatusTarget
    text: str
    posted_at: datetime


class _Bucket:
    """Insertion order of accepted URLs, with a later duplicate replacing text."""

    def __init__(self) -> None:
        self._accepted: dict[str, AcceptedObservation] = {}
        self._order: list[str] = []
        self.rejected: list[ObservationRejection] = []

    def plan(self) -> ObservationPlan:
        """Freeze the batch."""
        accepted = tuple(self._accepted[url] for url in self._order)
        return ObservationPlan(accepted=accepted, rejected=tuple(self.rejected))


def plan_observations(
    posts: tuple[ObservedPostInput, ...], as_of: datetime
) -> ObservationPlan:
    """Classify every post. One refusal does not drop the rest of the batch."""
    bucket = _Bucket()
    for post in posts:
        _include(bucket, classify_post(post, as_of))
    return bucket.plan()


def classify_post(
    post: ObservedPostInput, as_of: datetime
) -> AcceptedObservation | ObservationRejection:
    """Accept one recent status post, or the reason that item was refused."""
    cleaned_url = strip_controls(post.url)
    target = parse_status_url(cleaned_url)
    if target is None:
        return _reject(cleaned_url, REASON_NOT_STATUS_URL)
    text = strip_controls(post.text)
    if text == "":
        return _reject(cleaned_url, REASON_EMPTY_TEXT)
    reason = _handle_problem(strip_controls(post.handle), target.handle)
    if reason is not None:
        return _reject(cleaned_url, reason)
    posted_at = posted_at_from_snowflake(int(target.status_id))
    if not is_recent_status(posted_at, ensure_utc(as_of)):
        return _reject(cleaned_url, REASON_STALE_STATUS)
    parts = _AcceptedParts(post=post, target=target, text=text, posted_at=posted_at)
    return _accepted(parts)


def _include(bucket: _Bucket, item: AcceptedObservation | ObservationRejection) -> None:
    if isinstance(item, ObservationRejection):
        bucket.rejected.append(item)
        return
    if item.url not in bucket._accepted:
        bucket._order.append(item.url)
    bucket._accepted[item.url] = item


def _handle_problem(submitted: str, url_handle: str) -> str | None:
    if submitted == "":
        return REASON_EMPTY_HANDLE
    if submitted.casefold() != url_handle.casefold():
        return REASON_HANDLE_MISMATCH
    return None


def _reject(url: str, reason: str) -> ObservationRejection:
    return ObservationRejection(url=url, reason=reason)


def _accepted(parts: _AcceptedParts) -> AcceptedObservation:
    post = parts.post
    return AcceptedObservation(
        url=parts.target.canonical_url,
        handle=parts.target.handle,
        text=parts.text,
        likes=post.likes,
        reposts=post.reposts,
        replies=post.replies,
        views=post.views,
        observed_at=ensure_utc(post.observed_at),
        posted_at=parts.posted_at,
        source=SignalSource.X_BROWSER,
    )
