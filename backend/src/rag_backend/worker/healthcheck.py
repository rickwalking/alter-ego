"""Container healthcheck of the generation worker: is the dispatcher loop alive?

Exit 0 when the liveness file (``GENERATION_WORKER_ALIVE_FILE``, as the worker
reads it) was touched within the last 2 minutes (the
dispatcher touches it every 10 s), 1 otherwise. No network, no database.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path

from rag_backend.infrastructure.config.generation_queue_settings import (
    DEFAULT_WORKER_ALIVE_FILE,
)

MAX_AGE_SECONDS = 120
ALIVE_FILE_ENV = "GENERATION_WORKER_ALIVE_FILE"
EXIT_HEALTHY = 0
EXIT_UNHEALTHY = 1


def check(alive_file: str, now: float) -> int:
    """The exit code for a liveness file at ``alive_file``."""
    path = Path(alive_file)
    if not path.exists():
        return EXIT_UNHEALTHY
    if now - path.stat().st_mtime > MAX_AGE_SECONDS:
        return EXIT_UNHEALTHY
    return EXIT_HEALTHY


def alive_file(environ: Mapping[str, str]) -> str:
    """The liveness file the worker writes: its setting, else the default."""
    return environ.get(ALIVE_FILE_ENV) or DEFAULT_WORKER_ALIVE_FILE


if __name__ == "__main__":
    sys.exit(check(alive_file(os.environ), time.time()))
