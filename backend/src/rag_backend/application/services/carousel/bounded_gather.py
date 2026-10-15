"""Bounded-concurrency gather for per-slide LLM work (AE-0391)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

T = TypeVar("T")


async def gather_bounded(
    factories: Sequence[Callable[[], Awaitable[T]]],
    limit: int,
) -> list[T]:
    """Run the factories with at most ``limit`` in flight, results in order.

    Every task is allowed to settle before the first failure (in input order)
    is raised, so a failing slide never leaves sibling LLM calls running
    detached from the workflow.
    """
    semaphore = asyncio.Semaphore(max(1, limit))

    async def _run(factory: Callable[[], Awaitable[T]]) -> T:
        async with semaphore:
            return await factory()

    settled = await asyncio.gather(
        *(_run(factory) for factory in factories), return_exceptions=True
    )
    results: list[T] = []
    for outcome in settled:
        if isinstance(outcome, BaseException):
            raise outcome
        results.append(outcome)
    return results


__all__ = ["gather_bounded"]
