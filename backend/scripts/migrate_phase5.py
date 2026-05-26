#!/usr/bin/env python3
"""Run Phase 5 data migration against the configured database (MIG-001–004).

Usage:
    DATABASE_URL=postgresql+asyncpg://... uv run python scripts/migrate_phase5.py
    DATABASE_URL=... uv run python scripts/migrate_phase5.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from rag_backend.application.services.phase5_migration_service import Phase5MigrationService
from rag_backend.infrastructure.database.config import get_session_maker, init_db


async def main(*, dry_run: bool) -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 1

    await init_db(database_url)
    session_factory = get_session_maker()
    service = Phase5MigrationService()

    async with session_factory() as db:
        report = await service.run(db, dry_run=dry_run)

    mode = "DRY RUN" if dry_run else "COMMITTED"
    print(f"\nPhase 5 migration ({mode})")
    print(f"  Creative briefs updated: {report.creative_briefs_updated}")
    print(f"  Workflow states updated: {report.workflow_states_updated}")
    print(f"  Projects linked:         {report.projects_linked}")
    print(f"  Persona created:         {report.persona_created} ({report.persona_id})")
    print(f"  Rubric created:          {report.rubric_created} ({report.rubric_id})")
    if report.errors:
        print("  Errors:")
        for err in report.errors:
            print(f"    - {err}")
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 5 data migration")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without committing changes",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(dry_run=args.dry_run)))
