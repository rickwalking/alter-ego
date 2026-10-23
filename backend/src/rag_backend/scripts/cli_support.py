"""Shared entry point for the guarded one-shot maintenance scripts."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from rag_backend.infrastructure.config.settings import get_settings

EXIT_USAGE = 2

ModeValidator = Callable[[argparse.Namespace], str | None]
ScriptRunner = Callable[[argparse.Namespace], Coroutine[object, object, int]]
EngineRunner = Callable[[AsyncEngine], Coroutine[object, object, int]]


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


async def run_on_own_engine(run: EngineRunner) -> int:
    """Run ``run`` on a dedicated engine (no ``create_all``) and dispose of it."""
    engine = create_async_engine(
        get_settings().database_url, pool_pre_ping=True, hide_parameters=True
    )
    try:
        return await run(engine)
    finally:
        await engine.dispose()
