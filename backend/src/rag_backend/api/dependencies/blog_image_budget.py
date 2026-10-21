"""Per-post image budget reservation (also used by bulk generation).

The budget is **reserved before** the provider call, under the row lock, and
committed at once: the request locks the post (``SELECT ... FOR UPDATE``),
refuses with 429 at ``BLOG_IMAGE_COST_CAP``, counts one image in
``ai_generation_metadata.blog_image_generations`` and commits. Parallel
requests (or a parallel bulk-generation batch) therefore queue on the lock and the one
that finds the cap reached is refused; none can pass at ``cap - 1`` together.

The reservation is deliberately **kept** when the spend or the later write
fails (provider error, deleted section, 409): the provider may already have
billed the call, and the cap is a spend ceiling, not a count of stored images.

A per-post, per-event-loop ``asyncio.Lock`` serializes reservations inside one
process as well, so the guarantee also holds on engines without row locks
(SQLite in tests).

_RESERVATION_LOCKS holds one lock per post and event loop: an asyncio.Lock is bound to
the loop it first waited on, and tests and workers may run several loops. Locks are per
post so one post's reservation never waits on another's. The row lock (FOR UPDATE) is
the cross-process guarantee; this lock covers engines without row locks inside one
process.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID
from weakref import WeakKeyDictionary

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.resource_access import lock_blog_post
from rag_backend.application.services.blog.blog_image_budget import (
    count_one_image,
    within_budget,
)
from rag_backend.domain.constants.blog_editor import ERR_BLOG_IMAGE_BUDGET_EXHAUSTED

_RESERVATION_LOCKS: WeakKeyDictionary[
    asyncio.AbstractEventLoop, dict[str, asyncio.Lock]
] = WeakKeyDictionary()


def _reservation_lock(post_id: UUID | str) -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    locks = _RESERVATION_LOCKS.setdefault(loop, {})
    return locks.setdefault(str(post_id), asyncio.Lock())


@dataclass(frozen=True)
class BudgetReservation:
    """Reserve ``images`` generations of ``post_id`` against ``cap``."""

    post_id: UUID | str
    cap: int
    images: int = 1


def _exhausted() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=ERR_BLOG_IMAGE_BUDGET_EXHAUSTED,
    )


async def reserve_image_budget(
    db: AsyncSession, reservation: BudgetReservation
) -> None:
    """Lock, check and count the images now; commit (ends the transaction)."""
    async with _reservation_lock(reservation.post_id):
        locked = await lock_blog_post(db, reservation.post_id)
        metadata = locked.ai_generation_metadata
        current = dict(metadata) if isinstance(metadata, dict) else {}
        for _ in range(reservation.images):
            if not within_budget(current, reservation.cap):
                await db.rollback()
                raise _exhausted()
            current = count_one_image(current)
        locked.ai_generation_metadata = current
        await db.commit()


__all__ = ["BudgetReservation", "reserve_image_budget"]
