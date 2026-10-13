"""Canonical status-post URLs for the X web-search collector.

Only ``https://(x|twitter).com/<handle>/status/<id>`` is kept. twitter.com
is rewritten to x.com. The collector never requests either host.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

from rag_backend.modules.autopilot.constants import (
    X_CANONICAL_ORIGIN,
    X_MAX_AGE_HOURS,
    X_STATUS_URL_PATTERN,
)

_STATUS_URL = re.compile(X_STATUS_URL_PATTERN)


@dataclass(frozen=True, kw_only=True)
class XStatusTarget:
    """A status post reduced to the parts a resolver and a signal share."""

    handle: str
    status_id: str
    canonical_url: str


def parse_status_url(url: str) -> XStatusTarget | None:
    """Return the canonical status target, or None when ``url`` is not a post."""
    match = _STATUS_URL.match(url.strip())
    if match is None:
        return None
    handle = match.group(2)
    status_id = match.group(3)
    canonical = f"{X_CANONICAL_ORIGIN}/{handle}/status/{status_id}"
    return XStatusTarget(handle=handle, status_id=status_id, canonical_url=canonical)


def is_recent_status(posted_at: datetime, as_of: datetime) -> bool:
    """True when the post is not older than the 48 hour window."""
    cutoff = as_of - timedelta(hours=X_MAX_AGE_HOURS)
    return posted_at >= cutoff


def canonical_url(url: str) -> str:
    """Key used to dedupe the bundle: lower host, no fragment, no trailing slash."""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/")
    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        path,
        parts.query,
        "",
    ))
