"""Service API key check for /api/autopilot/* (AE-0351).

The dependency does not resolve a user. A missing setting disables the
feature (503). A missing or wrong key is 401. The plaintext key is never
logged; comparison is constant-time over the sha256 hex digests.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Annotated, NoReturn

from fastapi import Depends, HTTPException, Request, status

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.infrastructure.logging import get_logger
from rag_backend.modules.autopilot.constants import (
    DETAIL_API_KEY_INVALID,
    DETAIL_API_KEY_UNCONFIGURED,
    HEADER_API_KEY,
    LOG_API_KEY_DISABLED,
    LOG_API_KEY_REJECTED,
    REASON_KEY_MISMATCH,
    REASON_KEY_MISSING,
)

logger = get_logger()


def _configured_digest(settings: Settings) -> str | None:
    raw = settings.grokbot_api_key_sha256.get_secret_value().strip().lower()
    if not raw:
        return None
    return raw


def _presented_key(request: Request) -> str | None:
    value = request.headers.get(HEADER_API_KEY)
    if value is None or value == "":
        return None
    return value


def _digests_match(presented: str, expected_hex: str) -> bool:
    digest = hashlib.sha256(presented.encode(ENCODING_UTF8)).hexdigest()
    return hmac.compare_digest(digest, expected_hex)


def _disabled() -> NoReturn:
    logger.warning(LOG_API_KEY_DISABLED)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=DETAIL_API_KEY_UNCONFIGURED,
    )


def _reject(reason: str) -> NoReturn:
    logger.warning(LOG_API_KEY_REJECTED, reason=reason)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=DETAIL_API_KEY_INVALID,
    )


def require_autopilot_api_key(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Reject the request unless the scout key matches the configured digest."""
    expected = _configured_digest(settings)
    if expected is None:
        _disabled()
    presented = _presented_key(request)
    if presented is None:
        _reject(REASON_KEY_MISSING)
    if not _digests_match(presented, expected):
        _reject(REASON_KEY_MISMATCH)
