"""Prune old carousel checkpoints, keeping each thread's latest one.

Usage (backend container on prod; the checkpoint tables live in the app database):
    python -m rag_backend.scripts.checkpoint_prune
    python -m rag_backend.scripts.checkpoint_prune --write-threads threads.txt
    python -m rag_backend.scripts.checkpoint_prune --apply --threads threads.txt \\
        --pg-dump checkpoints.dump [--backup checkpoint-backup.jsonl]
    python -m rag_backend.scripts.checkpoint_prune --restore checkpoint-backup.jsonl

Without ``--apply`` it is a dry run: one line per eligible thread with its
project's state and the rows each table would lose; nothing is deleted.
``--write-threads`` saves the listed thread ids for Pedro to review and sign off.
``--apply`` prunes only the signed-off threads. It refuses unless
``pg_restore --list`` reads the ``--pg-dump`` archive (``pg_dump -Fc``) and finds
the data of the three checkpoint tables, and unless the carousel graph keeps no
``DeltaChannel`` state (rebuilt from the history this prune deletes). It writes
every row it deletes to the JSONL backup first, by default a new file under the
mounted output volume (``<output>/checkpoint-prune/``). ``--restore`` inserts a
JSONL backup back.

Exit codes: 0 ok, 1 refused (a check failed, a signed-off thread is no longer
eligible, the backup does not match, or nothing was deleted), 2 usage error.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from langgraph.channels import DeltaChannel
from langgraph.pregel import Pregel
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_backend.agents.carousel_workflow_graph import build_carousel_workflow_graph
from rag_backend.domain.constants.checkpoint_prune import (
    BACKUP_DIR_NAME,
    BACKUP_FILE_NAME,
    BACKUP_STAMP_FORMAT,
    ERR_DELTA_CHANNEL,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.checkpoint_prune import (
    PruneCandidate,
    PruneRefusedError,
    PruneRequest,
    apply_prune,
    find_candidates,
)
from rag_backend.infrastructure.database.checkpoint_prune_backup import (
    refuse,
    restore_backup,
    verify_pg_dump,
)
from rag_backend.scripts.cli_support import (
    EXIT_USAGE,
    GuardedCli,
    run_guarded_cli,
    run_on_own_engine,
)

EXIT_OK = 0
EXIT_REFUSED = 1
_BACKUP_DIR_MODE = 0o700
_ERR_APPLY_NEEDS_FILES = "--apply needs --threads and --pg-dump"
_ERR_FILES_NEED_APPLY = "--threads, --pg-dump and --backup only go with --apply"
_ERR_RESTORE_ALONE = "--restore goes alone"
_ERR_TTL_DAYS = "--ttl-days must be at least 1"
_ERR_NO_THREADS_FILE = "the --threads file does not exist"
_ERR_NO_PG_DUMP = "the --pg-dump file does not exist"
_ERR_NO_RESTORE_FILE = "the --restore file does not exist"
_ERR_BACKUP_EXISTS = "the --backup file already exists"
_HEADER = (
    "thread_id\tstatus\tphase_status\tworkflow_status\tpublic\tarchived\tupdated_at"
    "\tcheckpoints\twrites\tblobs"
)

__all__ = [
    "EXIT_OK",
    "EXIT_REFUSED",
    "EXIT_USAGE",
    "delta_channels",
    "main",
    "run_modes",
]


def build_parser() -> argparse.ArgumentParser:
    """CLI flags; a dry run unless ``--apply`` or ``--restore``."""
    parser = argparse.ArgumentParser(prog="checkpoint_prune", description=__doc__)
    parser.add_argument("--apply", action="store_true", help="prune signed-off threads")
    parser.add_argument(
        "--threads", type=Path, help="signed-off thread ids, one per line"
    )
    parser.add_argument(
        "--pg-dump", type=Path, help="pg_dump -Fc archive of the checkpoint tables"
    )
    parser.add_argument("--backup", type=Path, help="new file for the deleted rows")
    parser.add_argument("--restore", type=Path, help="JSONL backup to insert back")
    parser.add_argument(
        "--write-threads", type=Path, help="save the dry-run thread ids"
    )
    parser.add_argument("--ttl-days", type=int, help="override the checkpoint TTL")
    return parser


def _apply_files_error(args: argparse.Namespace) -> str | None:
    """The usage error for the files of ``--apply``."""
    if args.threads is None or args.pg_dump is None:
        return _ERR_APPLY_NEEDS_FILES
    if not args.threads.is_file():
        return _ERR_NO_THREADS_FILE
    if not args.pg_dump.is_file():
        return _ERR_NO_PG_DUMP
    if args.backup is not None and args.backup.exists():
        return _ERR_BACKUP_EXISTS
    return None


def _restore_error(args: argparse.Namespace) -> str | None:
    """The usage error for ``--restore``."""
    others = (args.apply, args.threads, args.pg_dump, args.backup, args.write_threads)
    if any(others):
        return _ERR_RESTORE_ALONE
    if not args.restore.is_file():
        return _ERR_NO_RESTORE_FILE
    return None


def _mode_error(args: argparse.Namespace) -> str | None:
    """The usage error for an incomplete or contradictory mode."""
    if args.ttl_days is not None and args.ttl_days < 1:
        return _ERR_TTL_DAYS
    if args.restore is not None:
        return _restore_error(args)
    if args.apply:
        return _apply_files_error(args)
    if any((args.threads, args.pg_dump, args.backup)):
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


def delta_channels() -> list[str]:
    """The ``DeltaChannel`` state of the carousel graph and of its subgraphs."""
    root = build_carousel_workflow_graph().compile()
    graphs = [("", root), *root.get_subgraphs(recurse=True)]
    return sorted(
        f"{namespace}:{name}" if namespace else name
        for namespace, compiled in graphs
        if isinstance(compiled, Pregel)
        for name, channel in compiled.channels.items()
        if isinstance(channel, DeltaChannel)
    )


def _default_backup() -> Path:
    """A new backup path under the mounted output volume."""
    output_root = Path(get_settings().carousel_output_dir).resolve().parent
    folder = output_root / BACKUP_DIR_NAME
    folder.mkdir(mode=_BACKUP_DIR_MODE, parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime(BACKUP_STAMP_FORMAT)
    return folder / BACKUP_FILE_NAME.format(stamp=stamp)


async def _checked_request(args: argparse.Namespace) -> PruneRequest:
    """Refuse on history-dependent graph state or an unreadable dump."""
    history = delta_channels()
    if history:
        raise refuse(ERR_DELTA_CHANNEL.format(channels=", ".join(history)))
    await verify_pg_dump(args.pg_dump)
    return PruneRequest(
        thread_ids=_signed_off(args.threads),
        cutoff=_cutoff(args),
        backup_path=args.backup or _default_backup(),
    )


async def _apply(engine: AsyncEngine, args: argparse.Namespace) -> int:
    try:
        request = await _checked_request(args)
        deleted = await apply_prune(engine, request)
    except PruneRefusedError as refused:
        print(f"REFUSED: {refused}", file=sys.stderr)
        return EXIT_REFUSED
    print(
        f"pruned threads={len(request.thread_ids)} checkpoints={deleted.checkpoints}"
        f" writes={deleted.writes} blobs={deleted.blobs} backup={request.backup_path}"
    )
    return EXIT_OK


async def _restore(engine: AsyncEngine, path: Path) -> int:
    try:
        restored = await restore_backup(engine, path)
    except PruneRefusedError as refused:
        print(f"REFUSED: {refused}", file=sys.stderr)
        return EXIT_REFUSED
    print(
        f"restored checkpoints={restored.checkpoints} writes={restored.writes}"
        f" blobs={restored.blobs} backup={path}"
    )
    return EXIT_OK


async def run_modes(engine: AsyncEngine, args: argparse.Namespace) -> int:
    """Dry run, prune, or restore; the exit code is the outcome."""
    if args.restore is not None:
        return await _restore(engine, args.restore)
    if args.apply:
        return await _apply(engine, args)
    return await _dry_run(engine, args)


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
