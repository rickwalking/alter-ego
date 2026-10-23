"""Prune old carousel checkpoints, keeping each thread's latest one.

Usage (backend container on prod; the checkpoint tables live in the app database):
    python -m rag_backend.scripts.checkpoint_prune
    python -m rag_backend.scripts.checkpoint_prune --write-threads threads.txt
    python -m rag_backend.scripts.checkpoint_prune --apply --threads threads.txt \\
        --backup checkpoint-backup.jsonl

Without ``--apply`` it is a dry run: one line per eligible thread with its
project's state and the rows each table would lose; nothing is deleted.
``--write-threads`` saves the listed thread ids for Pedro to review and sign off.
``--apply`` prunes only the signed-off threads, after writing every row it deletes
to the backup file (which must not exist yet).

Exit codes: 0 ok, 1 refused (a signed-off thread is no longer eligible, the
backup does not match, or nothing was deleted), 2 usage error.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.checkpoint_prune import (
    PruneCandidate,
    PruneRefusedError,
    PruneRequest,
    apply_prune,
    find_candidates,
)
from rag_backend.scripts.cli_support import (
    EXIT_USAGE,
    GuardedCli,
    run_guarded_cli,
    run_on_own_engine,
)

EXIT_OK = 0
EXIT_REFUSED = 1
_ERR_APPLY_NEEDS_FILES = "--apply needs --threads and --backup"
_ERR_FILES_NEED_APPLY = "--threads and --backup only go with --apply"
_HEADER = (
    "thread_id\tstatus\tphase_status\tworkflow_status\tpublic\tarchived\tupdated_at"
    "\tcheckpoints\twrites\tblobs"
)

__all__ = ["EXIT_OK", "EXIT_REFUSED", "EXIT_USAGE", "main", "run_modes"]


def build_parser() -> argparse.ArgumentParser:
    """CLI flags; a dry run unless ``--apply``."""
    parser = argparse.ArgumentParser(prog="checkpoint_prune", description=__doc__)
    parser.add_argument("--apply", action="store_true", help="prune signed-off threads")
    parser.add_argument(
        "--threads", type=Path, help="signed-off thread ids, one per line"
    )
    parser.add_argument("--backup", type=Path, help="new file for the deleted rows")
    parser.add_argument(
        "--write-threads", type=Path, help="save the dry-run thread ids"
    )
    parser.add_argument("--ttl-days", type=int, help="override the checkpoint TTL")
    return parser


def _mode_error(args: argparse.Namespace) -> str | None:
    """The usage error for an incomplete or contradictory mode."""
    files = args.threads is not None, args.backup is not None
    if args.apply and not all(files):
        return _ERR_APPLY_NEEDS_FILES
    if not args.apply and any(files):
        return _ERR_FILES_NEED_APPLY
    return None


def _cutoff(args: argparse.Namespace) -> datetime:
    ttl_days = args.ttl_days or get_settings().carousel_checkpoint_ttl_days
    return datetime.now(UTC) - timedelta(days=ttl_days)


def _line(candidate: PruneCandidate) -> str:
    rows = candidate.prunable
    return "\t".join((
        candidate.thread_id,
        candidate.status,
        candidate.phase_status,
        candidate.workflow_status,
        str(candidate.is_public).lower(),
        str(candidate.archived).lower(),
        candidate.updated_at.isoformat(),
        str(rows.checkpoints),
        str(rows.writes),
        str(rows.blobs),
    ))


async def _dry_run(engine: AsyncEngine, args: argparse.Namespace) -> int:
    candidates = await find_candidates(engine, _cutoff(args))
    print(_HEADER)
    for candidate in candidates:
        print(_line(candidate))
    if args.write_threads is not None:
        ids = "".join(f"{candidate.thread_id}\n" for candidate in candidates)
        args.write_threads.write_text(ids, encoding="utf-8")
    return EXIT_OK


def _signed_off(path: Path) -> tuple[str, ...]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return tuple(dict.fromkeys(line.strip() for line in lines if line.strip()))


async def run_modes(engine: AsyncEngine, args: argparse.Namespace) -> int:
    """Dry run, or prune the signed-off threads; the exit code is the outcome."""
    if not args.apply:
        return await _dry_run(engine, args)
    request = PruneRequest(
        thread_ids=_signed_off(args.threads),
        cutoff=_cutoff(args),
        backup_path=args.backup,
    )
    try:
        deleted = await apply_prune(engine, request)
    except PruneRefusedError as refused:
        print(f"REFUSED: {refused}", file=sys.stderr)
        return EXIT_REFUSED
    print(
        f"pruned threads={len(request.thread_ids)} checkpoints={deleted.checkpoints}"
        f" writes={deleted.writes} blobs={deleted.blobs} backup={request.backup_path}"
    )
    return EXIT_OK


async def _run_on_own_engine(args: argparse.Namespace) -> int:
    """Run the mode on a dedicated engine."""
    return await run_on_own_engine(lambda engine: run_modes(engine, args))


def main(argv: Sequence[str] | None = None) -> int:
    """Parse flags, run, return the process exit code."""
    return run_guarded_cli(
        GuardedCli(parser=build_parser(), validate=_mode_error, run=_run_on_own_engine),
        argv,
    )


if __name__ == "__main__":
    sys.exit(main())
