"""Constants of the generation worker's deploy drain.

A deploy sets the drain flag, waits until the busy marker is gone and only then
stops the worker. ``DRAIN_TTL_SECONDS`` is the ssh command timeout of the deploy:
a flag older than that belongs to a deploy that is gone, so it no longer pauses
the worker.
"""

from __future__ import annotations

from typing import Final

DRAIN_TTL_SECONDS: Final = 900.0
DRAIN_RETRY_DELAY_SECONDS: Final = 30
DRAIN_FILE_ENV: Final = "GENERATION_WORKER_DRAIN_FILE"
BUSY_FILE_ENV: Final = "GENERATION_WORKER_BUSY_FILE"
DRAIN_REASON: Final = "worker draining for a deploy"

LOG_DRAIN_REFUSED: Final = "generation_worker_drain_refused"
LOG_DRAIN_CLEARED: Final = "generation_worker_drain_cleared"

COMMAND_DRAIN: Final = "drain"
COMMAND_IDLE: Final = "idle"
COMMAND_CLEAR: Final = "clear"

EXIT_OK: Final = 0
EXIT_BUSY: Final = 1
EXIT_USAGE: Final = 2
USAGE: Final = "usage: python -m rag_backend.worker.drain_cli drain|idle|clear"

__all__ = [
    "BUSY_FILE_ENV",
    "COMMAND_CLEAR",
    "COMMAND_DRAIN",
    "COMMAND_IDLE",
    "DRAIN_FILE_ENV",
    "DRAIN_REASON",
    "DRAIN_RETRY_DELAY_SECONDS",
    "DRAIN_TTL_SECONDS",
    "EXIT_BUSY",
    "EXIT_OK",
    "EXIT_USAGE",
    "LOG_DRAIN_CLEARED",
    "LOG_DRAIN_REFUSED",
    "USAGE",
]
