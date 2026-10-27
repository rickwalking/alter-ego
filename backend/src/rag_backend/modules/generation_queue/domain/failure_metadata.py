"""Content-free failure metadata shared by recovery and generation events."""

from __future__ import annotations

import re

from rag_backend.modules.generation_queue.domain.recovery import failure_metadata

_SAFE_CODE = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_DEFAULT_ERROR_CODE = "generation_error"


def safe_failure_metadata(
    exc: Exception, error_code: str | None = None
) -> dict[str, str]:
    """The exception type and optional classified code, never its message."""
    failure = failure_metadata(exc)
    metadata = {"error_type": failure.exception_type[:64]}
    if error_code is None:
        return metadata
    safe_code = error_code if _SAFE_CODE.fullmatch(error_code) else _DEFAULT_ERROR_CODE
    metadata["error_code"] = safe_code
    return metadata


__all__ = ["safe_failure_metadata"]
