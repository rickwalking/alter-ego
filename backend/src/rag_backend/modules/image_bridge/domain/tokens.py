"""One-time callback tokens.

The plaintext token goes to the Grok Bot once, in the webhook body. Only its
SHA-256 hex digest is stored, and a presented token is compared in constant
time over the digests (the ``autopilot/api/auth.py`` pattern).

A decoy digest is compared when the job is unknown, so that path costs the same as a
wrong token and answers the same 401.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.modules.image_bridge.constants import CALLBACK_TOKEN_BYTES

_NO_JOB_DIGEST = hashlib.sha256(b"").hexdigest()


def new_callback_token() -> str:
    """A fresh url-safe random token (43 characters)."""
    return secrets.token_urlsafe(CALLBACK_TOKEN_BYTES)


def token_digest(token: str) -> str:
    """SHA-256 hex digest of a token."""
    return hashlib.sha256(token.encode(ENCODING_UTF8)).hexdigest()


def token_matches(presented: str | None, expected_digest: str | None) -> bool:
    """Constant-time check of a presented token against a stored digest."""
    digest = token_digest(presented or "")
    matched = hmac.compare_digest(digest, expected_digest or _NO_JOB_DIGEST)
    return bool(presented) and expected_digest is not None and matched
