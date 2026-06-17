"""Canonical distribution home accessor: ``blog_posts.distribution`` (AE-0204).

This module is the single accessor over the canonical home of a carousel's
distribution copy — the Instagram **caption** and the **LinkedIn posts**
(``linkedin_post_pt`` / ``linkedin_post_en``). Per AE-0204 these three fields move
from the embedded ``carousel_projects`` columns to the ``blog_posts.distribution``
JSONB column (mirroring the existing ``blog_posts.content`` JSONB pattern,
ADR-0006), so the embedded columns can later be dropped (AE-0205) without data
loss or a broken IG/LinkedIn publish.

It exposes exactly two operations over the canonical ``origin='carousel'``
``blog_posts`` row (joined on ``project_id``):

* :func:`write_distribution` — the **dual-write mirror**. Called from the
  carousel-blog write chokepoint (``sync_carousel_blog_post``) so every carousel
  write that lands the embedded copy ALSO lands it in the canonical home. The
  embedded columns are retained during the AE-0205 transition (reversible
  dual-write), but the canonical home — not the embedded column — is the source of
  truth every reader consumes.
* :func:`read_distribution` — the **read accessor**. Returns the canonical
  ``{caption, linkedin_post_pt, linkedin_post_en}`` payload for a project, or
  ``None`` when no carousel-origin row exists. Every application reader sources the
  three fields through this accessor (directly, or via the carousel repository
  overlay that stamps a freshly-loaded entity from the canonical home), so the
  embedded ORM columns have ZERO application readers for these fields (AE-0204).

``caption_en`` is deliberately NOT given a home here — it is write-dead and is
handled by AE-0206.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.blog_post import BlogPostOrigin
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

# Canonical ``blog_posts.distribution`` JSON keys — the single source of these
# field names for both the dual-write mirror and every reader.
DISTRIBUTION_CAPTION_KEY = "caption"
DISTRIBUTION_LINKEDIN_POST_PT_KEY = "linkedin_post_pt"
DISTRIBUTION_LINKEDIN_POST_EN_KEY = "linkedin_post_en"

DISTRIBUTION_KEYS: tuple[str, str, str] = (
    DISTRIBUTION_CAPTION_KEY,
    DISTRIBUTION_LINKEDIN_POST_PT_KEY,
    DISTRIBUTION_LINKEDIN_POST_EN_KEY,
)


def build_distribution(project: CarouselProject) -> dict[str, object]:
    """Build the canonical distribution payload from a carousel entity.

    The shape mirrors the ``blog_posts.distribution`` JSONB contract:
    ``{caption, linkedin_post_pt, linkedin_post_en}``, each ``str | None``. This is
    the single place the embedded carousel attributes are projected into the
    canonical shape (the dual-write mirror reads them here).
    """
    return {
        DISTRIBUTION_CAPTION_KEY: project.caption,
        DISTRIBUTION_LINKEDIN_POST_PT_KEY: project.linkedin_post_pt,
        DISTRIBUTION_LINKEDIN_POST_EN_KEY: project.linkedin_post_en,
    }


def _coerce_str_or_none(value: object) -> str | None:
    """Narrow a JSON value to ``str | None`` (no ``Any``) for the typed read."""
    return value if isinstance(value, str) else None


async def _carousel_blog_row(
    session: AsyncSession,
    project_id: str,
) -> BlogPostModel | None:
    """Return the project's ``origin='carousel'`` blog row, or ``None``."""
    query = select(BlogPostModel).where(
        BlogPostModel.project_id == project_id,
        BlogPostModel.origin == BlogPostOrigin.CAROUSEL.value,
    )
    result = await session.execute(query)
    return result.scalars().first()


async def write_distribution(
    session: AsyncSession,
    project: CarouselProject,
) -> None:
    """Mirror the carousel's distribution copy into the canonical home (flush only).

    No-op when no ``origin='carousel'`` row exists for the project: the row is
    created by the carousel-blog dual-write only for body-bearing carousels (and by
    the AE-0204 backfill for pre-existing ones), so a missing row means there is no
    canonical home to populate. The row is flushed (not committed) so it shares the
    caller's single transaction (the repository commits once).
    """
    row = await _carousel_blog_row(session, str(project.id))
    if row is None:
        return
    row.distribution = build_distribution(project)
    await session.flush()


async def read_distribution(
    session: AsyncSession,
    project_id: str,
) -> dict[str, str | None] | None:
    """Read the canonical distribution payload for a project, or ``None``.

    Returns the ``{caption, linkedin_post_pt, linkedin_post_en}`` payload sourced
    SOLELY from the ``origin='carousel'`` ``blog_posts.distribution`` column.
    Returns ``None`` when no carousel-origin row exists (so callers can preserve
    their legacy ``None``/empty defaults). Every application reader of the three
    fields routes through this accessor — the embedded columns are read-dead.
    """
    row = await _carousel_blog_row(session, project_id)
    if row is None:
        return None
    distribution = row.distribution or {}
    return {
        DISTRIBUTION_CAPTION_KEY: _coerce_str_or_none(
            distribution.get(DISTRIBUTION_CAPTION_KEY)
        ),
        DISTRIBUTION_LINKEDIN_POST_PT_KEY: _coerce_str_or_none(
            distribution.get(DISTRIBUTION_LINKEDIN_POST_PT_KEY)
        ),
        DISTRIBUTION_LINKEDIN_POST_EN_KEY: _coerce_str_or_none(
            distribution.get(DISTRIBUTION_LINKEDIN_POST_EN_KEY)
        ),
    }


__all__ = [
    "DISTRIBUTION_CAPTION_KEY",
    "DISTRIBUTION_KEYS",
    "DISTRIBUTION_LINKEDIN_POST_EN_KEY",
    "DISTRIBUTION_LINKEDIN_POST_PT_KEY",
    "build_distribution",
    "read_distribution",
    "write_distribution",
]
