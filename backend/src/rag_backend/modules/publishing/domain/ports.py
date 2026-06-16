"""Outbound ports for the publishing bounded context.

The publishing ports are:

* ``BlogPostRepository`` — blog-post persistence (re-exported, object-identity
  shim; see below). The publishing context reads/lists blog posts through this
  contract.
* ``CarouselRepository`` — carousel project persistence (re-exported,
  object-identity shim; see below). The publishing context reads a carousel
  project's public-visibility signal (for the carousel→blog projection) through
  this contract.
* ``CarouselReleasePort`` — the public-release (``is_public``) write contract for
  a carousel project (AE-0128). The carousel publish flow drives the
  ``is_public=True`` release through this port; its only adapter is the
  publishing ACL/owner, which is the sole publishing code touching the carousel
  ORM for this write.
* ``BlogVisibilityPort`` — the publish/unpublish status-write contract for a
  standalone blog post (AE-0128). The standalone blog publish/unpublish routes
  drive their visibility-status writes through this port (adapter: the ACL/owner).
* ``BlogSchedulePort`` — the scheduling write contract for a standalone blog post
  (AE-0128). The standalone blog schedule route + the scheduled-publish worker
  drive their schedule writes through this port (adapter: the ACL/owner).
* ``DistributionPublisher`` — the channel-delivery + distribution-read contract
  (AE-0129). The ``publish-instagram`` route distributes the carousel slides to
  Instagram and the ``generate-caption`` route reads the persisted caption through
  this port; its adapter (the channel publisher in infrastructure) wraps the Meta
  Instagram vendor adapter + the persisted caption copy, so the vendor/LLM SDK
  imports stay out of the publishing application/domain layers.

Per backend/CLAUDE.md, interfaces are :class:`typing.Protocol`, never ABCs, and
they are fully typed (no ``Any``). These Protocols let the publishing
APPLICATION/domain layers depend only on contracts — never on the blog/carousel
ORM directly; the concrete persistence adapters live in the publishing
infrastructure ACL/owner behind this facade (AE-0128).

**Re-export, not relocation (AE-0126 constraint).** ``CarouselRepository`` is the
shared Protocol defined in ``rag_backend.domain.protocols.repositories`` (imported
by the carousel routes, the workflow engine, services, and the container).
``BlogPostRepository`` is the concrete data-access class defined in
``rag_backend.infrastructure.database.blog_post_repository`` (imported by the blog
routes). Physically moving either would break those imports, so this phase keeps
both definitions where they are and merely **re-exports** them here. The legacy
import paths keep resolving to the IDENTICAL objects, while the publishing module
domain layer also exposes them as its own ports. This mirrors
``modules.editorial.domain.ports`` / ``modules.presentation.domain.ports`` exactly
(object-identity shims).

**No ORM in domain (AE-0128 constraint).** The three new write Protocols
(``CarouselReleasePort`` / ``BlogVisibilityPort`` / ``BlogSchedulePort``) speak
only in primitive/value types (ids, the optional scheduled instant). The carousel
project ENTITY is passed through ``object`` (the application layer holds the
canonical :class:`CarouselProject`; the port stays ORM-free and the adapter casts
it back) so neither this domain layer nor the application layer imports the ORM.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from rag_backend.domain.models.carousel import CarouselProject
from rag_backend.domain.protocols.repositories import CarouselRepository
from rag_backend.infrastructure.database.blog_post_repository import (
    BlogPostRepository,
)
from rag_backend.modules.publishing.domain.models import (
    BlogPostModel,
    DistributionResult,
    Publication,
)
from rag_backend.modules.publishing.domain.projections import (
    AnalyticsProjection,
    AnalyticsQuery,
    BlogListQuery,
    BoardProjection,
    BoardQuery,
    CalendarProjection,
    CalendarQuery,
    CarouselBlogI18nProjection,
    CarouselBlogProjection,
)


class DistributionPublisher(Protocol):
    """Channel-delivery + distribution-read contract for a release (AE-0129).

    The single seam through which the publishing context distributes a release to
    its outbound channels and reads its persisted per-channel copy. It speaks only
    in the publishing context's own types — the :class:`Publication` view and the
    :class:`DistributionResult` value object — and primitives, so neither the
    application nor the domain layer touches a vendor/LLM SDK. The concrete
    adapter (the channel publisher in ``infrastructure``) wraps the Meta Instagram
    vendor adapter + the persisted caption copy; the vendor SDK imports stay
    confined there.

    Behavior-preserving: ``publish_instagram`` forwards the EXACT caption +
    image-url payload to the vendor publisher and maps its result one-to-one;
    ``caption_for`` projects the already-persisted caption (no LLM call), identical
    to the pre-AE-0129 route read.
    """

    async def publish_instagram(
        self,
        caption: str,
        image_urls: list[str],
    ) -> DistributionResult:
        """Distribute the carousel slides to Instagram; return the channel result.

        Forwards the caption + the public image URLs to the channel adapter
        (byte-identical vendor payload) and maps the vendor outcome into a
        :class:`DistributionResult`.
        """
        ...

    def caption_for(self, publication: Publication) -> str:
        """Return the release's persisted social caption (empty string if unset).

        Projects the already-persisted caption from the :class:`Publication` view;
        no LLM call — identical to the legacy ``project.caption or ""`` read.
        """
        ...


class PublishingReadPort(Protocol):
    """Read-model projection contract for the public/editor READ surfaces (AE-0131).

    The single seam through which the publishing context serves the public carousel
    ``/blog`` (+lang), the content-calendar, the workflow-board, and the
    editorial-analytics dashboard. It returns the publishing context's own
    boundary-safe projection value objects (never the ORM, never ``Any``); the
    concrete adapter (the read-side ACL in ``infrastructure``) is the ONLY
    publishing code that touches the carousel/blog ORM for these reads.

    Behavior-preserving + additive (AE-0131): the carousel-blog projection reads
    the ``blog_posts`` ``origin='carousel'`` rows (AE-0127 backfill) when present,
    falling back per-field to the embedded carousel columns so the response is
    byte-identical; the calendar/board/analytics projections aggregate exactly the
    same rows the legacy route/services read.
    """

    async def project_carousel_blog(
        self,
        project: CarouselProject,
    ) -> CarouselBlogProjection | None:
        """Project the public carousel blog (default pt-BR), or ``None`` if absent.

        Returns ``None`` when the carousel has no generated blog body (the route
        maps that to the legacy 404); the ``project`` is already access-checked at
        the edge.
        """
        ...

    async def project_carousel_blog_i18n(
        self,
        project: CarouselProject,
        language: str,
    ) -> CarouselBlogI18nProjection | None:
        """Project the localized carousel blog, ``None`` if absent in ``language``."""
        ...

    async def project_calendar(self, query: CalendarQuery) -> CalendarProjection:
        """Project the content-calendar entries in the query's date range."""
        ...

    async def project_board(self, query: BoardQuery) -> BoardProjection:
        """Project the workflow-board phase columns for the caller's scope."""
        ...

    async def project_analytics(self, query: AnalyticsQuery) -> AnalyticsProjection:
        """Project the editorial-analytics summary + weekly velocity."""
        ...


class BlogPostCrudPort(Protocol):
    """Blog-post CRUD persistence-row contract for the thin blog routes (AE-0131).

    The seam through which the blog-post CRUD routes obtain their persistence rows
    so the routes themselves import no blog ORM/repository. The concrete adapter
    (the read-side ACL in ``infrastructure``) owns the blog ORM; the route keeps
    the access checks, audit/event/lock orchestration, and the single commit at the
    edge (byte-identical). ``new_post``/``get_post`` return the canonical
    :class:`BlogPostModel` (re-exported, identical object) the route stages in its
    own session and serializes via the response model.
    """

    def new_post(self, payload: dict[str, object]) -> BlogPostModel:
        """Build an unsaved blog row from the create payload (no session write)."""
        ...

    async def get_post(self, post_id: str) -> BlogPostModel | None:
        """Load a blog row by id through the request session, or ``None``."""
        ...

    async def list_summaries(
        self,
        query: BlogListQuery,
    ) -> tuple[list[BlogPostModel], int]:
        """List blog summaries + the total count (legacy ``list_summaries``)."""
        ...


class CarouselReleasePort(Protocol):
    """Public-release (``is_public``) write contract for a carousel project.

    The single seam through which the carousel publish flow makes a project
    publicly visible. The concrete adapter (the publishing ACL/owner) performs the
    byte-identical ``is_public=True`` / ``current_phase=published`` write through
    the carousel repository AND the carousel ORM row and commits via the platform
    Unit of Work — exactly the legacy ``crud.py:publish_carousel`` release write.
    """

    async def release_public(
        self,
        project: object,
        project_id: str,
    ) -> object:
        """Mark the carousel publicly released; return the updated entity.

        ``project`` is the canonical carousel project entity (passed as
        ``object`` so the domain port stays ORM-free); ``project_id`` is its id.
        Returns the updated carousel entity the route serializes (identical to the
        legacy ``repo.update_project`` return).
        """
        ...


class BlogVisibilityPort(Protocol):
    """Publish/unpublish status-write contract for a standalone blog post.

    The seam the standalone blog publish/unpublish routes drive their
    visibility-status writes through. The concrete adapter (the publishing
    ACL/owner) performs the byte-identical status / ``published_at`` writes on the
    blog row (flush only; the route owns the event emission + the single commit).
    """

    async def mark_published(self, post: object) -> None:
        """Set the blog row to PUBLISHED with ``published_at`` now (flush only)."""
        ...

    async def mark_unpublished(self, post: object) -> None:
        """Revert the blog row to DRAFT and clear publish stamps (flush only)."""
        ...


class BlogSchedulePort(Protocol):
    """Scheduling write contract for a standalone blog post.

    The seam the standalone blog schedule route + the scheduled-publish worker
    drive their schedule writes through. The concrete adapter (the publishing
    ACL/owner) performs the byte-identical ``scheduled_publish_at`` write + the
    scheduled-publish event emission (flush only; the route owns the commit), and
    the due-post sweep that publishes posts whose scheduled instant has passed.
    """

    async def schedule_publish(self, post: object, scheduled_at: datetime) -> None:
        """Stamp ``scheduled_publish_at`` + emit the scheduled event (flush only)."""
        ...

    async def process_due_posts(self) -> int:
        """Publish all posts whose scheduled time has passed; return the count."""
        ...


__all__ = [
    "BlogPostCrudPort",
    "BlogPostRepository",
    "BlogSchedulePort",
    "BlogVisibilityPort",
    "CarouselReleasePort",
    "CarouselRepository",
    "DistributionPublisher",
    "PublishingReadPort",
]
