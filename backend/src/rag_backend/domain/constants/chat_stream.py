"""SSE constants for chat streaming service."""

from __future__ import annotations

SSE_EVENT_TOKEN = "token"  # noqa: S105  — SSE event type name, not a password token
SSE_EVENT_COMPLETE = "complete"
SSE_EVENT_ERROR = "error"
SSE_KEEP_ALIVE_INTERVAL_SECONDS = 15
ERR_EMPTY_MESSAGE = "Message content cannot be empty"
