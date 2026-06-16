"""Request-scoped composition helper for the publishing module facade (AE-0128).

This is the HTTP-edge composition point for the publishing bounded context. It
assembles the request-scoped collaborators — the carousel repository (the
``CarouselRepository`` port), the existing scheduled-publish service, and the
AE-0128 :class:`LegacyPublishingAcl` (the sole carousel/blog ORM seam) — binds
them to the request ``AsyncSession``, wraps that same session in the platform Unit
of Work (the single commit owner, ADR-0009 §9), and hands them to
``bootstrap_module`` to build the public :class:`PublishingModule` facade.

Composition happens HERE — at the edge, inside ``api/dependencies/`` — never
inside the module's application code (which composes via ``bootstrap``). To keep
this edge module free of any NEW ``api -> infrastructure`` import (the
grandfathered baseline only allows the pre-existing edges), the infra-touching
collaborators (the request session, the carousel repository, and the
scheduled-publish service) are RESOLVED by the calling route module — which
already carries those grandfathered infra imports — and passed in via the typed
:class:`PublishingComposition` bundle. This module then performs only the
ORM-free wiring (the ACL, the UoW, and ``bootstrap_module``).

The route binds the facade to the EXACT same FastAPI-cached ``AsyncSession`` it
already uses (the carousel publish route's ``get_session``; the blog workflow
routes' ``get_db``) — a separate session would yield a second, uncommitted
transaction and break the byte-identical commit semantics. Mirrors
``api/dependencies/editorial.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rag_backend.modules.publishing import (
    ChannelDistributionPublisher,
    LegacyPublishingAcl,
    PublishingAdapters,
    PublishingModule,
    PublishingReadAcl,
    bootstrap_module,
)
from rag_backend.platform.database import SqlAlchemyUnitOfWork

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from rag_backend.application.services.scheduled_publish_service import (
        ScheduledPublishService,
    )
    from rag_backend.domain.protocols import SocialPublisher
    from rag_backend.modules.publishing import CarouselRepository


@dataclass(frozen=True)
class PublishingComposition:
    """Infra-resolved collaborators the route edge supplies for composition.

    Bundles the request-scoped ``AsyncSession``, the carousel repository, and the
    scheduled-publish service — all resolved by the calling route module (which
    carries the grandfathered infra imports) so this edge module stays free of any
    new ``api -> infrastructure`` import. Kept to a single grouped argument
    (backend/CLAUDE.md ≤3 args). ``with_read`` (AE-0131) requests the read
    projection + blog-CRUD ports backed by the read ACL bound to the same session
    (the carousel-blog/calendar/board/analytics + blog-CRUD routes set it; the
    write edges leave it ``False``).
    """

    session: AsyncSession
    carousel_repository: CarouselRepository
    scheduler: ScheduledPublishService | None = None
    social_publisher: SocialPublisher | None = None
    with_read: bool = False


def build_publishing_module(
    composition: PublishingComposition,
) -> PublishingModule:
    """Wire the request-scoped publishing facade from the route's collaborators.

    The same ``AsyncSession`` backs the carousel repository, the AE-0128 ACL, and
    the Unit of Work, so the release/visibility writes' flushes and the UoW's
    single commit share one transaction (ADR-0009 §9). ``platform`` is passed as
    ``None`` (the placeholder bootstrap signature; a real module builds adapters
    from ``rag_backend.platform`` once it ships).
    """
    acl = LegacyPublishingAcl(
        composition.session,
        composition.carousel_repository,
        composition.scheduler,
    )
    adapters = PublishingAdapters(
        carousel_repository=composition.carousel_repository,
        unit_of_work=SqlAlchemyUnitOfWork(composition.session),
        publishing_acl=acl,
        distribution_publisher=_build_distribution_publisher(
            composition.social_publisher
        ),
        read_acl=_build_read_acl(composition),
    )
    return bootstrap_module(platform=_PLATFORM_PLACEHOLDER, adapters=adapters)


def _build_read_acl(
    composition: PublishingComposition,
) -> PublishingReadAcl | None:
    """Build the AE-0131 read ACL bound to the request session when reads are needed.

    The carousel-blog/calendar/board/analytics + blog-CRUD read routes set
    ``with_read`` so the read + blog-CRUD ports are wired to the read ACL — the
    sole carousel/blog ORM read seam — bound to the EXACT same request session the
    route already uses. The write edges leave ``with_read`` ``False`` so the read
    ports stay unwired there.
    """
    if not composition.with_read:
        return None
    return PublishingReadAcl(composition.session)


def _build_distribution_publisher(
    social_publisher: SocialPublisher | None,
) -> ChannelDistributionPublisher | None:
    """Wrap the route-resolved social publisher in the AE-0129 channel adapter.

    The Meta Instagram vendor adapter (the ``SocialPublisher``) is resolved by the
    calling route (which carries the grandfathered ``get_instagram_publisher`` edge,
    keeping this edge module free of any new locator/infra import) and wrapped here
    in the publishing :class:`ChannelDistributionPublisher` so the distribution
    routes drive Instagram + the persisted caption/LinkedIn reads through the
    publishing facade + the distribution port. Absent (the carousel/blog release
    edges that never distribute), the distribution port stays unwired.
    """
    if social_publisher is None:
        return None
    return ChannelDistributionPublisher(social_publisher)


# Placeholder for the not-yet-built shared platform substrate. The publishing
# ``bootstrap_module`` accepts ``platform`` to demonstrate the ADR-0009 §9
# signature but ignores it during the behavior-preserving phase (a real module
# builds adapters from ``rag_backend.platform`` once it ships); any object
# satisfies the empty ``PlatformServices`` Protocol.
_PLATFORM_PLACEHOLDER: object = object()
