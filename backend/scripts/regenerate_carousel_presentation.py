#!/usr/bin/env python3
"""Explicit legacy carousel presentation regeneration (audit mode by default).

Reads existing PT/EN copy, validates it in audit mode, optionally repairs,
rerenders to a new artifact version, and preserves prior output under
<output_dir>/.rollback/<timestamp>/ for rollback.

Usage:
    uv run python scripts/regenerate_carousel_presentation.py --project-id UUID
    uv run python scripts/regenerate_carousel_presentation.py --project-id UUID --render
    uv run python scripts/regenerate_carousel_presentation.py --project-id UUID --dry-run

Flags:
    --project-id            Carousel project UUID (required)
    --dry-run               Audit only; do not render or activate artifacts
    --render                Re-render slides and promote a new artifact version
    --repair                Reserved for bounded repair (not wired in this CLI)
    --target-policy VERSION Presentation policy to apply on render
                            (default: hero_lower_third_v1)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from uuid import UUID

from rag_backend.application.services.carousel.artifact_build_service import (
    CarouselArtifactBuildService,
)
from rag_backend.application.services.carousel.legacy_presentation_regeneration import (
    LegacyRegenerationError,
    RegenerationCommand,
    RegenerationResult,
    default_target_policy_version,
    regenerate_legacy_presentation,
)
from rag_backend.application.services.carousel.refinement_service import (
    CarouselRefinementService,
)
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import close_db, get_session, init_db
from rag_backend.infrastructure.logging import get_logger, setup_logging

logger = get_logger()


def _parse_args() -> RegenerationCommand:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--repair", action="store_true")
    parser.add_argument(
        "--target-policy",
        default=default_target_policy_version(),
    )
    args = parser.parse_args()
    dry_run = bool(args.dry_run) or not bool(args.render)
    return RegenerationCommand(
        project_id=UUID(str(args.project_id)),
        dry_run=dry_run,
        repair=bool(args.repair),
        render=bool(args.render),
        target_policy_version=str(args.target_policy),
    )


def _print_audit(command: RegenerationCommand, result: RegenerationResult) -> None:
    audit = result.audit
    print(f"project_id={audit.project_id}")
    print(f"current_policy={audit.current_policy_version}")
    print(f"target_policy={audit.target_policy_version}")
    print(f"validation_status={audit.validation_status}")
    print(f"artifact_health_ok={audit.artifact_health_ok}")
    if audit.prior_artifact_version:
        print(f"prior_artifact_version={audit.prior_artifact_version}")
    if audit.backup_path is not None:
        print(f"rollback_root={audit.backup_path}")
    for note in audit.notes:
        print(f"note={note}")
    for message in audit.violation_messages:
        print(f"violation={message}")
    for error in audit.artifact_health_errors:
        print(f"artifact_error={error}")
    if command.render and not command.dry_run:
        print(f"rendered={result.rendered}")
        print(f"artifact_version={result.artifact_version}")
        if result.manifest_path is not None:
            print(f"manifest_path={result.manifest_path}")


async def _run(command: RegenerationCommand) -> int:
    settings = get_settings()
    setup_logging(debug=settings.debug)
    await init_db(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    container = get_container()
    artifact_build = CarouselArtifactBuildService()
    try:
        async for session in get_session():
            refinement = CarouselRefinementService(
                repository=PostgresCarouselRepository(session),
                llm_service=container.llm_service(),
                image_registry=container.image_provider_registry(),
                export_service=container.export_service(),
                pdf_slide_builder=container.pdf_slide_builder(),
                strategy_registry=container.strategy_registry(),
            )
            result = await regenerate_legacy_presentation(
                session,
                refinement,
                artifact_build,
                command,
            )
            _print_audit(command, result)
            return 0
    except (ValueError, LegacyRegenerationError, TypeError) as exc:
        logger.warning("legacy_regeneration_failed", error=str(exc))
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        await close_db()
    return 1


def main() -> int:
    command = _parse_args()
    return asyncio.run(_run(command))


if __name__ == "__main__":
    raise SystemExit(main())
