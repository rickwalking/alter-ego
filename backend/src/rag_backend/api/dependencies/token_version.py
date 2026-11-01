"""Refuse an access token issued before the user's last password change.

A password change bumps ``users.token_version``; every access token carries the
version it was issued with (claim ``tv``). The dependencies that load the user
for a request compare the two with :func:`reject_stale_token`, so a stale token
costs no extra database read and answers 401 exactly like an expired one.

A token without ``tv`` was issued before versions existed and counts as version
0, so the tokens alive at deploy time keep working until the user's first
change. A ``tv`` that is not a whole number is treated as stale.
"""

from collections.abc import Mapping

from fastapi import HTTPException, status

from rag_backend.api.constants import (
    ERR_INVALID_OR_EXPIRED_TOKEN,
    WWW_AUTHENTICATE_BEARER,
)
from rag_backend.domain.constants import (
    JWT_CLAIM_TOKEN_VERSION,
    TOKEN_VERSION_BEFORE_VERSIONING,
)


def claimed_token_version(payload: Mapping[str, object]) -> int | None:
    """The version a token was issued with: 0 without ``tv``, None if malformed."""
    value = payload.get(JWT_CLAIM_TOKEN_VERSION, TOKEN_VERSION_BEFORE_VERSIONING)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def is_current_token(payload: Mapping[str, object], token_version: int) -> bool:
    """Whether the token was issued at the user's current ``token_version``."""
    return claimed_token_version(payload) == token_version


def reject_stale_token(payload: Mapping[str, object], token_version: int) -> None:
    """Refuse (401, like an expired token) a token from before a password change."""
    if is_current_token(payload, token_version):
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ERR_INVALID_OR_EXPIRED_TOKEN,
        headers=WWW_AUTHENTICATE_BEARER,
    )


__all__ = ["claimed_token_version", "is_current_token", "reject_stale_token"]
