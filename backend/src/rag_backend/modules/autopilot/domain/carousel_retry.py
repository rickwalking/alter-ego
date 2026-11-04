"""The owner's carousel Retry on Telegram: button, callback and port. Pure."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.carousel_retry_constants import (
    BUTTON_CAROUSEL_RETRY,
    CALLBACK_CAROUSEL_RETRY_PATTERN,
    CALLBACK_CAROUSEL_RETRY_PREFIX,
    TEXT_CAROUSEL_RETRY_BY_REFUSAL,
    TEXT_CAROUSEL_RETRY_REFUSED,
)
from rag_backend.modules.autopilot.domain.messages import (
    InlineButton,
    InlineKeyboard,
    callback_data,
)

_CALLBACK = re.compile(CALLBACK_CAROUSEL_RETRY_PATTERN)


@dataclass(frozen=True, kw_only=True)
class CarouselRetryRequest:
    """Retry ``project_id`` for ``actor_id`` (the autopilot owner's user)."""

    project_id: str
    actor_id: str


@dataclass(frozen=True, kw_only=True)
class CarouselRetryOutcome:
    """Accepted with the phase being redone, or the refusal code."""

    accepted: bool
    phase: str = ""
    refusal: str = ""


class CarouselRetrier(Protocol):
    """The generation queue's owner Retry, on the webhook's session."""

    async def retry(self, request: CarouselRetryRequest) -> CarouselRetryOutcome:
        """Stage the Retry in the caller's transaction, or refuse it."""
        ...

    async def deliver(self) -> None:
        """Announce the accepted run starts; after the caller's commit."""
        ...

    def discard(self) -> None:
        """Forget the run starts of a rolled-back transaction."""
        ...


def carousel_retry_keyboard(run_id: UUID) -> InlineKeyboard:
    """ "Tentar de novo" for an escalated run's carousel."""
    button = InlineButton(
        text=BUTTON_CAROUSEL_RETRY,
        callback_data=callback_data(CALLBACK_CAROUSEL_RETRY_PREFIX, run_id),
    )
    return InlineKeyboard(rows=((button,),))


def parse_carousel_retry(data: str) -> UUID | None:
    """The run of an ``ap:cr:<uuid>`` button; None for any other data."""
    match = _CALLBACK.fullmatch(data)
    if match is None:
        return None
    return UUID(match.group(1))


def refusal_text(refusal: str) -> str:
    """The owner's message for a refused Retry."""
    return TEXT_CAROUSEL_RETRY_BY_REFUSAL.get(
        refusal, TEXT_CAROUSEL_RETRY_REFUSED.format(code=refusal)
    )


__all__ = [
    "CarouselRetrier",
    "CarouselRetryOutcome",
    "CarouselRetryRequest",
    "carousel_retry_keyboard",
    "parse_carousel_retry",
    "refusal_text",
]
