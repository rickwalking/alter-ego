"""The deploy drain of the generation worker: a drain flag and a busy marker.

Pedro's decision (2026-11-02): a deploy pauses new job pickup and lets the job in
flight reach its next phase boundary before it stops the worker. Two files in the
worker's own ``/tmp`` (a tmpfs, so a restart starts with neither) carry it:

- the drain flag, set by the deploy (``drain_cli drain``). While it is fresh the
  job entrypoint refuses to claim a job (it goes back to the queue untouched) and
  a running drive yields at its next phase boundary, as on SIGTERM. A flag older
  than ``DRAIN_TTL_SECONDS`` belongs to a deploy that is gone and is ignored, and
  the worker removes it when it starts, so a failed deploy never pauses it for good;
- the busy marker, present while a generation job is inside the entrypoint. It is
  set before the drain check, so a job that passed the check is always seen busy
  by a deploy that set the flag after it.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from rag_backend.infrastructure.config.generation_queue_settings import (
    DEFAULT_WORKER_BUSY_FILE,
    DEFAULT_WORKER_DRAIN_FILE,
)
from rag_backend.worker.constants import (
    BUSY_FILE_ENV,
    DRAIN_FILE_ENV,
    DRAIN_TTL_SECONDS,
)

Clock = Callable[[], float]


@dataclass(frozen=True, kw_only=True)
class DrainFiles:
    """Where the drain flag and the busy marker live."""

    drain: Path
    busy: Path

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> DrainFiles:
        """The files the worker uses: its settings' env vars, else the defaults."""
        return cls(
            drain=Path(environ.get(DRAIN_FILE_ENV) or DEFAULT_WORKER_DRAIN_FILE),
            busy=Path(environ.get(BUSY_FILE_ENV) or DEFAULT_WORKER_BUSY_FILE),
        )


class DrainSwitch:
    """Read and write the drain flag and the busy marker."""

    def __init__(self, files: DrainFiles, clock: Clock = time.time) -> None:
        self._files = files
        self._clock = clock

    def request(self) -> None:
        """Set (or refresh) the drain flag."""
        self._files.drain.touch()

    def clear(self) -> None:
        """Remove the drain flag; the worker claims jobs again."""
        self._files.drain.unlink(missing_ok=True)

    def reset(self) -> None:
        """At worker start: no drain flag and no busy marker from an older process."""
        self.clear()
        self._files.busy.unlink(missing_ok=True)

    def is_draining(self) -> bool:
        """True while the drain flag exists and is younger than its time-to-live."""
        try:
            set_at = self._files.drain.stat().st_mtime
        except FileNotFoundError:
            return False
        return self._clock() - set_at <= DRAIN_TTL_SECONDS

    def is_busy(self) -> bool:
        """True while a generation job is inside the entrypoint."""
        return self._files.busy.exists()

    def mark_busy(self) -> None:
        """Create the busy marker."""
        self._files.busy.touch()

    def mark_idle(self) -> None:
        """Remove the busy marker."""
        self._files.busy.unlink(missing_ok=True)


class JobGate:
    """Counts the generation jobs in flight and answers whether one may be claimed."""

    def __init__(self, switch: DrainSwitch) -> None:
        self._switch = switch
        self._in_flight = 0

    @asynccontextmanager
    async def admit(self) -> AsyncIterator[bool]:
        """Mark the worker busy, then yield False when it is draining.

        The busy marker stays for the whole block, also when the job raises, and
        is removed when the last job in flight leaves.
        """
        self._in_flight += 1
        self._switch.mark_busy()
        try:
            yield not self._switch.is_draining()
        finally:
            self._in_flight -= 1
            if self._in_flight == 0:
                self._switch.mark_idle()


def drive_stopping(shutdown: asyncio.Event, switch: DrainSwitch) -> Callable[[], bool]:
    """When a drive yields at its phase boundary: on shutdown or while drained."""
    return lambda: shutdown.is_set() or switch.is_draining()


__all__ = ["Clock", "DrainFiles", "DrainSwitch", "JobGate", "drive_stopping"]
