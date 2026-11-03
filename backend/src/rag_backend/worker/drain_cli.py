"""The deploy's handle on the worker drain: ``python -m rag_backend.worker.drain_cli``.

Run inside the generation worker container (``docker compose exec``):

- ``drain`` sets the drain flag (exit 0);
- ``idle`` exits 0 when no generation job is in flight, 1 while one is;
- ``clear`` removes the drain flag (exit 0).

Any other argument exits 2. No settings, no network, no database: like the
healthcheck it reads only the file locations from the environment.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping, Sequence

from rag_backend.worker.constants import (
    COMMAND_CLEAR,
    COMMAND_DRAIN,
    COMMAND_IDLE,
    EXIT_BUSY,
    EXIT_OK,
    EXIT_USAGE,
    USAGE,
)
from rag_backend.worker.drain import DrainFiles, DrainSwitch


def _drain(switch: DrainSwitch) -> int:
    switch.request()
    return EXIT_OK


def _idle(switch: DrainSwitch) -> int:
    return EXIT_BUSY if switch.is_busy() else EXIT_OK


def _clear(switch: DrainSwitch) -> int:
    switch.clear()
    return EXIT_OK


_COMMANDS: dict[str, Callable[[DrainSwitch], int]] = {
    COMMAND_DRAIN: _drain,
    COMMAND_IDLE: _idle,
    COMMAND_CLEAR: _clear,
}


def main(argv: Sequence[str], environ: Mapping[str, str]) -> int:
    """Run the one command in ``argv``; the exit code of the deploy step."""
    command = _COMMANDS.get(argv[0]) if len(argv) == 1 else None
    if command is None:
        sys.stderr.write(USAGE + "\n")
        return EXIT_USAGE
    return command(DrainSwitch(DrainFiles.from_environ(environ)))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ))
