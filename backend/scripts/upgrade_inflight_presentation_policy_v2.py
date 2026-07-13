#!/usr/bin/env python3
"""Run-once migration: upgrade in-flight carousels to presentation policy v2.

⚠️ DEPLOY-GATED ON AE-0311 — DO NOT RUN IN PROD BEFORE THE REPAIR ENDPOINT /
"Fix issues" button (AE-0311) IS LIVE. The v2 casing rules are warning-severity,
so this migration surfaces new visible warnings on every in-flight review.
Without a working fix button those warnings degrade the review UX with no
one-click remedy. The rules/severity/v2 policy deploy any time; this migration
is the separate, AE-0311-gated deliverable (AE-0312 Decision Log r4).

WHAT IT DOES
------------
For every NON-completed project not already on v2:
  1. Bumps ``carousel_projects.presentation_policy_version`` to v2.
  2. Re-validates the project's ``localized_slides`` under v2 and stores the
     fresh severity-aware ``presentation_validation`` report in the workflow
     checkpoint (re-labeling alone would leave the stale v1 report served
     verbatim — AE-0312 Decision Log r5).
Completed projects are left untouched (frozen artifacts + policy version).

SAFETY
------
- Idempotent + resumable: rows already on v2 are skipped, so a re-run continues
  from where it stopped.
- Batched: commits every 50 projects with progress logs. Re-validation is pure
  CPU over already-loaded slide data, so runtime is bounded.
- Down migration (``--downgrade``): restores v1 for non-completed rows and
  re-validates under v1 (deterministic, reproduces the prior stored report).

USAGE (run inside the backend container, AFTER the AE-0311 deploy)
    docker compose exec backend uv run python \
        scripts/upgrade_inflight_presentation_policy_v2.py [--dry-run] [--downgrade]
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import cast

from sqlalchemy import select

from rag_backend.agents.carousel_workflow import CarouselWorkflowEngine
from rag_backend.agents.harness import build_checkpointer
from rag_backend.application.services.carousel.presentation_policy_upgrade import (
    build_policy_downgrade_updates,
    build_policy_upgrade_updates,
    should_upgrade_project,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import (
    close_db,
    get_session_maker,
    init_db,
)
from rag_backend.infrastructure.database.models import CarouselProjectModel
from rag_backend.infrastructure.logging import get_logger, setup_logging

logger = get_logger()

_BATCH_SIZE = 50
_COMPLETED_STATUS = "completed"
_POLICY_VERSION_COLUMN = "presentation_policy_version"


@dataclass(frozen=True)
class UpgradeConfig:
    """Migration run configuration."""

    dry_run: bool = False
    downgrade: bool = False


@dataclass(frozen=True)
class MigrationContext:
    """Wiring shared across the batch loop."""

    engine: CarouselWorkflowEngine
    config: UpgradeConfig


async def _revalidate_checkpoint(
    ctx: MigrationContext,
    project_id: str,
) -> bool:
    """Re-validate one project's localized slides under the target policy."""
    state = await ctx.engine.get_state(project_id)
    if state is None:
        return False
    values = dict(state)
    updates = (
        build_policy_downgrade_updates(values)
        if ctx.config.downgrade
        else build_policy_upgrade_updates(values)
    )
    if ctx.config.dry_run:
        return True
    await ctx.engine.update_state(project_id, updates)
    return True


def _target_version(config: UpgradeConfig) -> str:
    if config.downgrade:
        return DEFAULT_PRESENTATION_POLICY_VERSION
    return PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2


async def _process_project(
    ctx: MigrationContext,
    project: CarouselProjectModel,
) -> bool:
    """Bump the DB column and re-validate the checkpoint for one project."""
    target = _target_version(ctx.config)
    status = str(project.status)
    current_version = cast("str | None", project.presentation_policy_version)
    if not ctx.config.downgrade and not should_upgrade_project(status, current_version):
        return False
    if ctx.config.downgrade and status == _COMPLETED_STATUS:
        return False
    await _revalidate_checkpoint(ctx, str(project.id))
    if not ctx.config.dry_run:
        # Old-style Column (untyped); setattr keeps the typed write mypy-clean.
        setattr(project, _POLICY_VERSION_COLUMN, target)
    logger.info(
        "presentation_policy_upgrade_project",
        project_id=str(project.id),
        target_version=target,
        dry_run=ctx.config.dry_run,
    )
    return True


async def _run(config: UpgradeConfig) -> int:
    settings = get_settings()
    setup_logging(debug=settings.debug)
    await init_db(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    try:
        async with AsyncExitStack() as stack:
            checkpointer = await build_checkpointer(settings, stack)
            if checkpointer is None:
                logger.error("presentation_policy_upgrade_no_checkpointer")
                return 1
            engine = CarouselWorkflowEngine(checkpointer=checkpointer)
            ctx = MigrationContext(engine=engine, config=config)
            processed = await _run_batches(ctx)
            logger.info("presentation_policy_upgrade_done", processed=processed)
        return 0
    finally:
        await close_db()


async def _run_batches(ctx: MigrationContext) -> int:
    processed = 0
    async with get_session_maker()() as session:
        result = await session.execute(
            select(CarouselProjectModel).where(
                CarouselProjectModel.status != _COMPLETED_STATUS
            )
        )
        projects = list(result.scalars().all())
        for index, project in enumerate(projects, start=1):
            if await _process_project(ctx, project):
                processed += 1
            if index % _BATCH_SIZE == 0:
                await session.commit()
                logger.info("presentation_policy_upgrade_batch", committed=index)
        await session.commit()
    return processed


def _parse_args() -> UpgradeConfig:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--downgrade", action="store_true")
    args = parser.parse_args()
    return UpgradeConfig(dry_run=bool(args.dry_run), downgrade=bool(args.downgrade))


def main() -> int:
    return asyncio.run(_run(_parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
