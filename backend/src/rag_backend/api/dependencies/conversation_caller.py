"""Who is calling a conversation endpoint: a signed-in user and/or a visitor token."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from rag_backend.api.dependencies.auth import get_optional_user
from rag_backend.api.middleware.auth import get_anon_cookie_payloads
from rag_backend.domain.models import User

ANON_CLAIM_CONVERSATION_ID = "conversation_id"


@dataclass(frozen=True)
class ConversationCaller:
    """The caller's identity for conversation access checks.

    ``anon_conversation_ids`` are the conversations the visitor's valid
    ``anon_token`` cookies (one per conversation, scoped to its URLs) were
    issued for; missing, expired, tampered or non-anonymous tokens add nothing.
    """

    user: User | None = None
    anon_conversation_ids: frozenset[str] = frozenset()


def anon_conversation_id(payload: dict[str, object] | None) -> str | None:
    """The conversation id claim of a decoded anonymous token, if any."""
    if payload is None:
        return None
    claim = payload.get(ANON_CLAIM_CONVERSATION_ID)
    return claim if isinstance(claim, str) else None


async def get_conversation_caller(
    user: Annotated[User | None, Depends(get_optional_user)],
    anon_payloads: Annotated[
        list[dict[str, object]], Depends(get_anon_cookie_payloads)
    ],
) -> ConversationCaller:
    """Resolve the signed-in user and the visitor's anonymous conversations."""
    ids = (anon_conversation_id(payload) for payload in anon_payloads)
    return ConversationCaller(
        user=user,
        anon_conversation_ids=frozenset(
            conversation_id for conversation_id in ids if conversation_id
        ),
    )


__all__ = [
    "ConversationCaller",
    "anon_conversation_id",
    "get_conversation_caller",
]
