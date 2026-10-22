"""Shared entry point for the guarded one-shot maintenance scripts."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass

EXIT_USAGE = 2

ModeValidator = Callable[[argparse.Namespace], str | None]
ScriptRunner = Callable[[argparse.Namespace], Coroutine[object, object, int]]


@dataclass(frozen=True)
class GuardedCli:
    """The parser, mode validator and async runner of one maintenance script."""

    parser: argparse.ArgumentParser
    validate: ModeValidator
    run: ScriptRunner


def run_guarded_cli(cli: GuardedCli, argv: Sequence[str] | None = None) -> int:
    """Parse flags, reject an invalid mode with ``EXIT_USAGE``, else run the script."""
    args = cli.parser.parse_args(argv)
    error = cli.validate(args)
    if error is not None:
        print(f"ERROR: {error}", file=sys.stderr)
        return EXIT_USAGE
    return asyncio.run(cli.run(args))
