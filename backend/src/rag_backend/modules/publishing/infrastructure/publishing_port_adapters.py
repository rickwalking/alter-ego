"""Concrete adapters for the publishing outbound ports (AE-0128).

These adapters are the infrastructure backing for the publishing domain ports
(``rag_backend.modules.publishing.domain.ports``). They keep the publishing
APPLICATION/domain layers free of the carousel/blog ORM and the concrete
persistence: every write port the application depends on is satisfied here by
**delegating** to the AE-0128 :class:`LegacyPublishingAcl` (the sole carousel/blog
ORM seam), which in turn performs the byte-identical legacy write + commit
boundary.

Behavior-preserving: no adapter mutates an ORM row or commits itself — each
forwards to the ACL's byte-identical path, so the ``is_public`` release write, the
blog publish/unpublish status writes, and the scheduling writes are untouched.
Mirrors the editorial ``editorial_port_adapters`` module (AE-0111).
"""

from __future__ import annotations

from datetime import datetime

from rag_backend.domain.models import CarouselProject
from rag_backend.modules.publishing.domain.models import BlogPostModel
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
from rag_backend.modules.publishing.infrastructure.legacy_publishing_acl import (
    LegacyPublishingAcl,
)
from rag_backend.modules.publishing.infrastructure.publishing_read_acl import (
    PublishingReadAcl,
)


class AclCarouselReleaseAdapter:
    """:class:`CarouselReleasePort` backed by the publishing ACL / owner.

    Forwards the carousel ``is_public`` public-release write to the ACL, which
    performs the byte-identical entity + ORM write and the single commit.
    """

    def __init__(self, acl: LegacyPublishingAcl) -> None:
        self._acl = acl

    async def release_public(self, project: object, project_id: str) -> object:
        """Run the carousel public-release write via the ACL → single owner."""
        return await self._acl.release_public(project, project_id)


class AclBlogVisibilityAdapter:
    """:class:`BlogVisibilityPort` backed by the publishing ACL / owner.

    Forwards the standalone blog publish/unpublish status writes to the ACL (flush
    only; the route owns the event emission + the single commit).
    """

    def __init__(self, acl: LegacyPublishingAcl) -> None:
        self._acl = acl

    async def mark_published(self, post: object) -> None:
        """Set the blog row PUBLISHED via the ACL (flush only)."""
        await self._acl.mark_published(post)

    async def mark_unpublished(self, post: object) -> None:
        """Revert the blog row to DRAFT via the ACL (flush only)."""
        await self._acl.mark_unpublished(post)


class AclBlogScheduleAdapter:
    """:class:`BlogSchedulePort` backed by the publishing ACL / owner.

    Forwards the standalone blog schedule write + the due-post sweep to the ACL,
    which delegates UNCHANGED to the existing scheduled-publish service.
    """

    def __init__(self, acl: LegacyPublishingAcl) -> None:
        self._acl = acl

    async def schedule_publish(self, post: object, scheduled_at: datetime) -> None:
        """Stamp the schedule + emit the scheduled event via the ACL (flush only)."""
        await self._acl.schedule_publish(post, scheduled_at)

    async def process_due_posts(self) -> int:
        """Run the due-post publish sweep via the ACL → scheduled-publish service."""
        return await self._acl.process_due_posts()


class AclPublishingReadAdapter:
    """:class:`PublishingReadPort` backed by the publishing read ACL (AE-0131).

    Forwards the carousel-blog (+lang), content-calendar, workflow-board, and
    editorial-analytics projections to the read ACL — the sole carousel/blog ORM
    read seam — which returns the byte-identical legacy reads as projection value
    objects.
    """

    def __init__(self, acl: PublishingReadAcl) -> None:
        self._acl = acl

    async def project_carousel_blog(
        self,
        project: CarouselProject,
    ) -> CarouselBlogProjection | None:
        """Project the public carousel blog (default pt-BR) via the read ACL."""
        return await self._acl.project_carousel_blog(project)

    async def project_carousel_blog_i18n(
        self,
        project: CarouselProject,
        language: str,
    ) -> CarouselBlogI18nProjection | None:
        """Project the localized carousel blog via the read ACL."""
        return await self._acl.project_carousel_blog_i18n(project, language)

    async def project_calendar(self, query: CalendarQuery) -> CalendarProjection:
        """Project the content-calendar entries via the read ACL."""
        return await self._acl.project_calendar(query)

    async def project_board(self, query: BoardQuery) -> BoardProjection:
        """Project the workflow-board phase columns via the read ACL."""
        return await self._acl.project_board(query)

    async def project_analytics(self, query: AnalyticsQuery) -> AnalyticsProjection:
        """Project the editorial-analytics summary + velocity via the read ACL."""
        return await self._acl.project_analytics(query)


class AclBlogPostCrudAdapter:
    """:class:`BlogPostCrudPort` backed by the publishing read ACL (AE-0131).

    Forwards the blog-post CRUD persistence-row reads/builds to the read ACL (the
    sole blog ORM seam) so the thin blog routes import no blog ORM/repository; the
    route keeps the access checks + audit/event/lock orchestration + the commit.
    """

    def __init__(self, acl: PublishingReadAcl) -> None:
        self._acl = acl

    def new_post(self, payload: dict[str, object]) -> BlogPostModel:
        """Build an unsaved blog row from the create payload via the read ACL."""
        return self._acl.new_post(payload)

    async def get_post(self, post_id: str) -> BlogPostModel | None:
        """Load a blog row by id via the read ACL, or ``None``."""
        return await self._acl.get_post(post_id)

    async def list_summaries(
        self,
        query: BlogListQuery,
    ) -> tuple[list[BlogPostModel], int]:
        """List blog summaries + total count via the read ACL."""
        return await self._acl.list_summaries(query)


__all__ = [
    "AclBlogPostCrudAdapter",
    "AclBlogScheduleAdapter",
    "AclBlogVisibilityAdapter",
    "AclCarouselReleaseAdapter",
    "AclPublishingReadAdapter",
]
