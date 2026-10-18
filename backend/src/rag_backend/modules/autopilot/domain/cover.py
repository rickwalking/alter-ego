"""GrokBot slide-1 covers: upload form rules, topic rules, credit (AE-0418).

Pure. The caller supplies the stored covers and the clock. A topic's cover is
checked last among the per-topic rules and rejects only that topic, with
``field: "cover.asset_id"``. A ``screenshot`` must come from one of the
topic's sources; both sides are compared after the same normalisation the
topic sources get (an X status URL becomes its canonical x.com form).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlsplit
from uuid import UUID

from rag_backend.domain.constants.slide_cover import (
    COVER_CREDIT_WWW_PREFIX,
    COVER_CREDIT_X_TEMPLATE,
    COVER_KIND_SCREENSHOT,
    COVER_KINDS,
    ERR_COVER_ASSET_KIND_INVALID,
    ERR_COVER_ASSET_SOURCE_MISSING,
)
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.modules.autopilot.cover_constants import (
    COVER_MAX_AGE_HOURS,
    REASON_COVER_ASSET_EXPIRED,
    REASON_COVER_ASSET_UNKNOWN,
    REASON_COVER_ASSET_USED,
    REASON_COVER_SOURCE_INVALID,
)
from rag_backend.modules.autopilot.domain.topic_text import is_http_url, strip_controls
from rag_backend.modules.autopilot.domain.x_status import (
    canonical_url,
    parse_status_url,
)


@dataclass(frozen=True, kw_only=True)
class CoverAsset:
    """One uploaded cover: its creator asset, kind, source and first user."""

    asset_id: UUID
    creator_asset_id: UUID
    kind: str
    source_url: str | None
    width: int
    height: int
    created_at: datetime
    topic_candidate_id: UUID | None = None
    # The creator asset's artifact-relative path (where it is staged).
    staged_path: str = ""

    @property
    def is_used(self) -> bool:
        """True once a stored topic references the cover."""
        return self.topic_candidate_id is not None


@dataclass(frozen=True, kw_only=True)
class CoverForm:
    """The upload's form fields, before the image is read."""

    kind: str | None
    source_url: str | None


@dataclass(frozen=True, kw_only=True)
class CoverFacts:
    """The covers the batch names, the clock, and ids already taken in it."""

    assets: Mapping[UUID, CoverAsset] = field(default_factory=dict)
    now: datetime | None = None
    claimed: frozenset[UUID] = frozenset()


@dataclass(frozen=True, kw_only=True)
class CoverCheck:
    """One topic's cover reference and its canonical sources."""

    asset_id: str
    sources: tuple[str, ...]


def form_problem(form: CoverForm) -> str | None:
    """The upload code a bad ``kind`` / missing screenshot source earns."""
    if form.kind not in COVER_KINDS:
        return ERR_COVER_ASSET_KIND_INVALID
    if form.kind == COVER_KIND_SCREENSHOT and clean_source(form.source_url) is None:
        return ERR_COVER_ASSET_SOURCE_MISSING
    return None


def clean_source(source_url: str | None) -> str | None:
    """The stored source of a screenshot: an http(s) URL, canonical, or None."""
    cleaned = strip_controls(source_url or "")
    if not is_http_url(cleaned):
        return None
    return source_key(cleaned)


def source_key(url: str) -> str:
    """The comparison key of a URL: canonical X status, else ``canonical_url``."""
    cleaned = canonical_url(url)
    status = parse_status_url(cleaned)
    if status is not None:
        return status.canonical_url
    return cleaned


def parse_asset_id(raw: str) -> UUID | None:
    """The asset UUID, or None for anything else (``cover_asset_unknown``)."""
    try:
        return UUID(raw.strip())
    except ValueError:
        return None


def cover_reason(check: CoverCheck, facts: CoverFacts) -> str | None:
    """Why the topic's cover is refused, or None when it may be attached."""
    asset_id = parse_asset_id(check.asset_id)
    asset = facts.assets.get(asset_id) if asset_id is not None else None
    if asset is None:
        return REASON_COVER_ASSET_UNKNOWN
    if facts.now is not None and is_expired(asset, facts.now):
        return REASON_COVER_ASSET_EXPIRED
    if asset.is_used or asset.asset_id in facts.claimed:
        return REASON_COVER_ASSET_USED
    if asset.kind == COVER_KIND_SCREENSHOT and not _from_sources(asset, check):
        return REASON_COVER_SOURCE_INVALID
    return None


def is_expired(asset: CoverAsset, now: datetime) -> bool:
    """True once the cover is older than the 6-hour window."""
    return asset.created_at < expiry_cutoff(now)


def expiry_cutoff(now: datetime) -> datetime:
    """Covers created before this instant have expired."""
    return now - timedelta(hours=COVER_MAX_AGE_HOURS)


def _from_sources(asset: CoverAsset, check: CoverCheck) -> bool:
    if asset.source_url is None:
        return False
    keys = {source_key(source) for source in check.sources}
    return source_key(asset.source_url) in keys


def cover_credit(source_url: str | None) -> str:
    """``@handle · X`` for an X post, else the host without ``www.``."""
    if not source_url:
        return ""
    status = parse_status_url(canonical_url(source_url))
    if status is not None:
        return COVER_CREDIT_X_TEMPLATE.format(handle=status.handle)
    host = urlsplit(source_url).hostname or ""
    return host.removeprefix(COVER_CREDIT_WWW_PREFIX)


def slide_cover_for(asset: CoverAsset) -> SlideCover:
    """The project field for ``asset`` (the creator asset, staged path, credit)."""
    return SlideCover(
        asset_id=asset.creator_asset_id,
        kind=asset.kind,
        staged_path=asset.staged_path,
        credit=cover_credit(asset.source_url)
        if asset.kind == COVER_KIND_SCREENSHOT
        else "",
    )


__all__ = [
    "CoverAsset",
    "CoverCheck",
    "CoverFacts",
    "CoverForm",
    "clean_source",
    "cover_credit",
    "cover_reason",
    "expiry_cutoff",
    "form_problem",
    "is_expired",
    "parse_asset_id",
    "slide_cover_for",
    "source_key",
]
