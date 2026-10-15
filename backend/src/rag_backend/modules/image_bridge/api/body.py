"""Bounded request-body reading for the callback route (AE-0393).

nginx caps the location at 16 MB; this enforces the same cap in the app so
a direct or chunked request cannot make the worker buffer more.
"""

from __future__ import annotations

from fastapi import Request

from rag_backend.modules.image_bridge.constants import (
    HEADER_CONTENT_LENGTH,
    MAX_CALLBACK_BODY_BYTES,
)


class BodyTooLargeError(ValueError):
    """The body passed ``MAX_CALLBACK_BODY_BYTES`` while streaming."""


def declared_too_large(request: Request) -> bool:
    """True when ``Content-Length`` already exceeds the cap."""
    declared = request.headers.get(HEADER_CONTENT_LENGTH, "")
    return declared.isdigit() and int(declared) > MAX_CALLBACK_BODY_BYTES


async def read_capped_body(request: Request) -> bytes:
    """The whole body, or ``BodyTooLargeError`` once it passes the cap."""
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_CALLBACK_BODY_BYTES:
            raise BodyTooLargeError
        chunks.append(chunk)
    return b"".join(chunks)
