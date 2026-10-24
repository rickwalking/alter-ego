"""Draft rows of the blog generation entry points (ADR-0025).

* :func:`live_post_id_for_project` — the 409 guard of ``from-carousel``: ANY
  ``blog_posts`` row with the project id counts (draft, under review, approved,
  scheduled, published or hidden); hidden bad posts are rebuilt separately.
* :func:`create_generation_draft` — a ``draft`` row with the bootstrap
  ``blog.v2`` document (zero sections, legal only while in progress) and a
  fresh lease. A ``from-carousel`` row is the carousel's canonical
  distribution home, so it starts with the carousel's saved caption and
  LinkedIn posts rather than an empty ``distribution``.
* :func:`restart_generation` — the owner's retry on the SAME row: a new lease
  and attempt, ``lock_version`` bumped (so a stale task of the old attempt is
  fenced out); compare-and-set so two concurrent retries cannot both start.

The caller (the route) owns the transaction and commits.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.ai_disclosure import AI_DISCLOSURE_GENERATED
from rag_backend.domain.constants.blog_document import BLOG_SCHEMA_V2
from rag_backend.domain.constants.blog_post import BlogPostOrigin, BlogPostStatus
from rag_backend.domain.constants.distribution import (
    DISTRIBUTION_CAPTION_KEY,
    DISTRIBUTION_LINKEDIN_POST_EN_KEY,
    DISTRIBUTION_LINKEDIN_POST_PT_KEY,
)
from rag_backend.domain.models.blog_generation import GenerationLease
from rag_backend.domain.models.blog_generation_state import GenerationStart, started
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel


def bootstrap_content() -> dict[str, object]:
    """The in-progress document: no cover, no sections yet (ADR-0025)."""
    return {
        "schema": BLOG_SCHEMA_V2,
        "cover": None,
        "sections": [],
        "translations": {},
        "quality": None,
    }


@dataclass(frozen=True)
class GenerationDraftSpec:
    """The new draft row of one generation request."""

    title: str
    slug: str
    origin: str
    author_id: str
    start: GenerationStart
    project_id: str | None = None


@dataclass(frozen=True)
class RestartSpec:
    """A retry: the row, the version the caller saw, and the new attempt."""

    post_id: str
    seen_lock_version: int
    start: GenerationStart


async def live_post_id_for_project(db: AsyncSession, project_id: str) -> str | None:
    """The id of any blog row of the project (hard delete is the only removal)."""
    result = await db.execute(
        select(BlogPostModel.id).where(BlogPostModel.project_id == project_id).limit(1)
    )
    found = result.scalar_one_or_none()
    return str(found) if found is not None else None


async def _carousel_distribution(
    db: AsyncSession, spec: GenerationDraftSpec
) -> dict[str, object]:
    """The carousel's saved copy for a ``from-carousel`` row; empty otherwise."""
    if spec.origin != BlogPostOrigin.CAROUSEL.value or spec.project_id is None:
        return {}
    row = (
        await db.execute(
            select(
                CarouselProjectModel.caption,
                CarouselProjectModel.linkedin_post_pt,
                CarouselProjectModel.linkedin_post_en,
            ).where(CarouselProjectModel.id == spec.project_id)
        )
    ).one_or_none()
    if row is None:
        return {}
    caption, linkedin_pt, linkedin_en = row
    return {
        DISTRIBUTION_CAPTION_KEY: caption,
        DISTRIBUTION_LINKEDIN_POST_PT_KEY: linkedin_pt,
        DISTRIBUTION_LINKEDIN_POST_EN_KEY: linkedin_en,
    }


async def create_generation_draft(
    db: AsyncSession, spec: GenerationDraftSpec
) -> GenerationLease:
    """Stage (flush) the draft row and return the run's lease.

    A post written by the blog writer is labelled AI-generated.
    """
    distribution = await _carousel_distribution(db, spec)
    post = BlogPostModel.from_entity({
        "id": str(uuid.uuid4()),
        "project_id": spec.project_id,
        "origin": spec.origin,
        "title": spec.title,
        "slug": spec.slug,
        "status": BlogPostStatus.DRAFT.value,
        "content": bootstrap_content(),
        "distribution": distribution,
        "author_id": spec.author_id,
        "ai_generation_metadata": started({}, spec.start),
        "ai_disclosure_label": AI_DISCLOSURE_GENERATED,
    })
    db.add(post)
    await db.flush()
    return GenerationLease(
        post_id=str(post.id), lease_id=spec.start.lease_id, lock_version=1
    )


async def restart_generation(
    db: AsyncSession, spec: RestartSpec
) -> GenerationLease | None:
    """New lease/attempt on the same row; ``None`` when the row moved meanwhile."""
    row = await db.execute(
        select(BlogPostModel.ai_generation_metadata).where(
            BlogPostModel.id == spec.post_id
        )
    )
    metadata = row.scalar_one_or_none()
    next_version = spec.seen_lock_version + 1
    result = await db.execute(
        update(BlogPostModel)
        .where(
            BlogPostModel.id == spec.post_id,
            BlogPostModel.lock_version == spec.seen_lock_version,
        )
        .values(
            ai_generation_metadata=started(metadata, spec.start),
            lock_version=next_version,
        )
        .execution_options(synchronize_session=False)
    )
    if cast(CursorResult[object], result).rowcount != 1:
        return None
    return GenerationLease(
        post_id=spec.post_id, lease_id=spec.start.lease_id, lock_version=next_version
    )


__all__ = [
    "GenerationDraftSpec",
    "RestartSpec",
    "bootstrap_content",
    "create_generation_draft",
    "live_post_id_for_project",
    "restart_generation",
]
