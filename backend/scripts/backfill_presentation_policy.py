#!/usr/bin/env python3
"""Backfill carousel presentation_policy_version for legacy projects.

Alembic migration 0008_carousel_presentation_contract already sets NULL rows to
legacy_neon_v2 on upgrade. Use this script when operators need a dry-run report
or to re-apply the backfill outside Alembic.

Usage:
    uv run python scripts/backfill_presentation_policy.py [--dry-run] [--project-id ID]

Flags:
    --dry-run       Print rows that would be updated without writing to DB
    --project-id    Limit to a single project UUID
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg

from rag_backend.domain.constants.carousel_presentation import (
    LEGACY_PRESENTATION_POLICY_VERSION,
)

_DSN_ENV = "DATABASE_URL"
_MSG_DSN = "Set DATABASE_URL environment variable"
_MIGRATION_NOTE = (
    "Migration 0008_carousel_presentation_contract sets presentation_policy_version "
    f"to {LEGACY_PRESENTATION_POLICY_VERSION!r} for NULL rows during upgrade."
)


async def _get_connection() -> asyncpg.Connection:
    dsn = os.environ.get(_DSN_ENV)
    if not dsn:
        print(_MSG_DSN, file=sys.stderr)
        sys.exit(1)
    dsn = dsn.replace("postgresql+asyncpg", "postgresql")
    return await asyncpg.connect(dsn)


async def _count_candidates(
    conn: asyncpg.Connection,
    project_id: str | None,
) -> list[asyncpg.Record]:
    if project_id:
        return await conn.fetch(
            """
            SELECT id, presentation_policy_version
            FROM carousel_projects
            WHERE id = $1 AND presentation_policy_version IS NULL
            """,
            project_id,
        )
    return await conn.fetch(
        """
        SELECT id, presentation_policy_version
        FROM carousel_projects
        WHERE presentation_policy_version IS NULL
        """
    )


async def _apply_backfill(
    conn: asyncpg.Connection,
    project_id: str | None,
) -> int:
    if project_id:
        result = await conn.execute(
            """
            UPDATE carousel_projects
            SET presentation_policy_version = $1
            WHERE id = $2 AND presentation_policy_version IS NULL
            """,
            LEGACY_PRESENTATION_POLICY_VERSION,
            project_id,
        )
    else:
        result = await conn.execute(
            """
            UPDATE carousel_projects
            SET presentation_policy_version = $1
            WHERE presentation_policy_version IS NULL
            """,
            LEGACY_PRESENTATION_POLICY_VERSION,
        )
    return int(result.split()[-1])


async def run(project_id: str | None, *, dry_run: bool) -> int:
    conn = await _get_connection()
    try:
        rows = await _count_candidates(conn, project_id)
        print(_MIGRATION_NOTE)
        if not rows:
            print("No projects require presentation policy backfill.")
            return 0
        print(f"Found {len(rows)} project(s) with NULL presentation_policy_version.")
        for row in rows:
            print(f"  - {row['id']}")
        if dry_run:
            print("Dry run only; no database rows updated.")
            return 0
        updated = await _apply_backfill(conn, project_id)
        print(f"Updated {updated} project(s) to {LEGACY_PRESENTATION_POLICY_VERSION!r}.")
        return 0
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--project-id", default="")
    args = parser.parse_args()
    project_id = str(args.project_id).strip() or None
    return asyncio.run(run(project_id, dry_run=bool(args.dry_run)))


if __name__ == "__main__":
    raise SystemExit(main())
