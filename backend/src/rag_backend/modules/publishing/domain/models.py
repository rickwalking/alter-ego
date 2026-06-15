"""Domain entities and value objects for the publishing bounded context.

The publishing context owns the *release + distribution contract* over a content
item: the blog post aggregate (over the ``blog_posts`` row), the carousel→blog
read projection (:class:`Publication`), the distribution channels a release
targets, and the schedule a release follows. This module defines its own new,
fully-typed value objects — :class:`BlogPost`, :class:`Publication`,
:class:`DistributionChannel`, :class:`PublishingSchedule` — and **re-exports** the
existing blog/carousel types so existing callers keep resolving to the IDENTICAL
objects.

**Re-export, not relocation (AE-0126 constraint).** The blog workflow status
enum stays at ``rag_backend.domain.constants.blog_post.BlogPostStatus``; the blog
ORM row stays at ``rag_backend.infrastructure.database.models.blog_post``; the
carousel project entity stays at ``rag_backend.domain.models.carousel``. This
module re-exports them under the publishing domain namespace WITHOUT moving or
modifying the canonical definitions, so identity/isinstance checks and the legacy
persistence adapters keep working during the behavior-preserving phase.

The :class:`BlogPost` aggregate is a typed VIEW over the canonical blog row: it
exposes the publishing-relevant fields (identity, slug, status, schedule, lock
version) as the publishing context's own read model. The carousel ORM uses the
legacy ``Column(...)`` declaration style (no ``Mapped[...]``), so its instance
attributes type as ``Column[T]`` under mypy; :meth:`BlogPost.from_model` reads
them through explicit :func:`typing.cast` (no ``Any``) — the only seam that
touches the ORM column shapes.

**AE-0127 forward note.** The additive ``origin`` field (carousel-derived vs.
native blog) is intentionally NOT defined here — AE-0127 adds it via an additive
migration + backfill. :class:`BlogPost` is shaped so AE-0127 can add an
``origin`` field/property without restructuring this view.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import cast
from uuid import UUID

from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.models.carousel import CarouselProject
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.modules.publishing.domain.release import (
    ReleasePhase,
    ReleaseState,
)


@dataclass(frozen=True)
class BlogPost:
    """The publishing aggregate VIEW over a single ``blog_posts`` row.

    A typed, immutable read model exposing the publishing-relevant fields of a
    blog post — identity, slug/title, workflow status, the scheduled publish
    instant, and the optimistic ``lock_version``. It wraps the canonical
    :class:`BlogPostModel` (re-exported, identical object) without owning the blog
    ORM or its editorial authoring; it only projects the fields the release +
    distribution paths read. The ``origin`` field is deferred to AE-0127.
    """

    id: str
    slug: str
    title: str
    status: BlogPostStatus
    lock_version: int
    project_id: str | None = None
    scheduled_publish_at: datetime | None = None
    published_at: datetime | None = None

    @property
    def release_state(self) -> ReleaseState:
        """The publishing release-lifecycle state derived from the blog status."""
        return ReleaseState(status=self.status)

    @classmethod
    def from_model(cls, model: BlogPostModel) -> BlogPost:
        """Build the publishing aggregate view from a canonical blog row.

        Reads the legacy ``Column``-typed instance attributes through explicit
        casts (no ``Any``); this is the single seam that depends on the ORM
        column shapes. ``status`` is coerced into the canonical
        :class:`BlogPostStatus` (no new strings).
        """
        return cls(
            id=cast(str, model.id),
            slug=cast(str, model.slug),
            title=cast(str, model.title),
            status=_coerce_status(cast("str | None", model.status)),
            lock_version=cast(int, model.lock_version),
            project_id=cast("str | None", model.project_id),
            scheduled_publish_at=cast("datetime | None", model.scheduled_publish_at),
            published_at=cast("datetime | None", model.published_at),
        )


def _coerce_status(status: str | None) -> BlogPostStatus:
    """Coerce a raw status string into the canonical enum, defaulting to DRAFT."""
    if status is None:
        return BlogPostStatus.DRAFT
    try:
        return BlogPostStatus(status)
    except ValueError:
        return BlogPostStatus.DRAFT


@dataclass(frozen=True)
class Publication:
    """Read projection of a carousel project as a publishable item (carousel→blog).

    The publishing context's VIEW over a carousel project that has been (or may
    be) surfaced as a public blog/homepage item. It wraps the canonical
    :class:`CarouselProject` (re-exported, identical object) and exposes only the
    publishing-relevant signals — the project identity, its public-visibility
    flag, and its display title. It does NOT own the carousel aggregate, its
    editorial workflow, or its presentation contract; the full carousel→blog
    projection lands in AE-0131.
    """

    project: CarouselProject

    @property
    def project_id(self) -> UUID:
        """The identifier of the underlying carousel project."""
        return self.project.id

    @property
    def is_public(self) -> bool:
        """Whether the carousel project is publicly released (homepage/blog)."""
        return self.project.is_public

    @property
    def title(self) -> str | None:
        """The carousel project's display title, when set."""
        return self.project.title


class DistributionChannelKind(StrEnum):
    """The kind of outbound channel a release can be distributed to.

    Names the distribution surfaces the publishing context targets. This is the
    publishing module's own value language (not a re-export); the distribution
    extraction + the per-channel adapters land in AE-0129. No channel
    side-effects are wired in AE-0126.
    """

    BLOG = "blog"
    HOMEPAGE = "homepage"
    NEWSLETTER = "newsletter"
    SOCIAL = "social"


@dataclass(frozen=True)
class DistributionChannel:
    """A configured outbound channel a release targets.

    A fully-typed value object pairing a :class:`DistributionChannelKind` with an
    ``enabled`` flag. AE-0126 defines the contract only; the concrete per-channel
    distribution adapters + the additive outbox are wired in AE-0129/0130.
    """

    kind: DistributionChannelKind
    enabled: bool = True


@dataclass(frozen=True)
class PublishingSchedule:
    """The schedule a content release follows.

    A fully-typed value object capturing the optional scheduled publish instant
    and whether the release is held for manual approval before going out. It is a
    read-side contract in AE-0126 (no scheduler is wired); the auto-publish
    behavior cutover is DEFERRED to a later phase.
    """

    scheduled_at: datetime | None = None
    requires_manual_release: bool = True

    @property
    def is_scheduled(self) -> bool:
        """Whether a future publish instant has been set for this release."""
        return self.scheduled_at is not None


__all__ = [
    "BlogPost",
    "BlogPostModel",
    "BlogPostStatus",
    "CarouselProject",
    "DistributionChannel",
    "DistributionChannelKind",
    "Publication",
    "PublishingSchedule",
    "ReleasePhase",
    "ReleaseState",
]
