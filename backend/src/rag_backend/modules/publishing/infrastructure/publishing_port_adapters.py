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

from rag_backend.modules.publishing.infrastructure.legacy_publishing_acl import (
    LegacyPublishingAcl,
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


__all__ = [
    "AclBlogScheduleAdapter",
    "AclBlogVisibilityAdapter",
    "AclCarouselReleaseAdapter",
]
