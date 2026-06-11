#!/usr/bin/env python3
"""Recovery/backfill CLI for carousel image generation records.

Scans existing carousel projects for slide image files on disk and creates
recovered generation records without inventing provider IDs. Also reports
projects with relative output_dir paths that need normalization.

Usage:
    uv run python scripts/recover_carousel_image_generations.py [--dry-run] [--project-id ID]

Flags:
    --dry-run       Print what would be done without writing to DB
    --project-id    Limit to a single project UUID
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import asyncpg

from rag_backend.domain.enums.run_mode import RunMode

_DSN_ENV = "DATABASE_URL"
_STATUS_SUCCEEDED = "succeeded"
_STATUS_RECOVERED = "recovered"
_STATUS_FAILED = "failed"
_DIR_CAROUSELS = "output/carousels"
_MSG_DSN = "Set DATABASE_URL environment variable"
_MSG_NO_PROJECTS = "No carousel projects found to process"
_IMAGES_DIR_NAME = "images"

_SLIDE_FILENAME_PREFIX = "slide_"
_SLIDE_IMAGE_EXTENSION = ".jpg"
_MIN_JPEG_BYTES = 1024

# asyncpg Record column name constants
_COL_ID = "id"
_COL_OUTPUT_DIR = "output_dir"
_COL_IMAGE_MODEL = "image_model"
_COL_IMAGE_STYLE = "image_style"
_COL_SLIDE_NUMBER = "slide_number"
_COL_IMAGE_PATH = "image_path"
_COL_GENERATION_KEY = "generation_key"


@dataclass
class _RecoverProjectOptions:
    """Command object for recovering a single project's image generations.

    Bundles all parameters for recover_project() to keep it at 1 argument
    (instead of 4) and follow the command object pattern.
    """

    conn: asyncpg.Connection
    project: asyncpg.Record
    slides: list[asyncpg.Record]
    run_mode: RunMode


@dataclass
class _SlideProcessingContext:
    """Command object bundling context for processing carousel slides.

    Replaces scattered individual parameters (previously run_mode, project,
    images_dir, existing_keys were passed separately) with a single command
    object that enforces the 'no boolean parameter' pattern.
    """

    conn: asyncpg.Connection
    images_dir: Path
    existing_keys: set[str]
    project: asyncpg.Record
    run_mode: RunMode


async def _get_connection() -> asyncpg.Connection:
    dsn = os.environ.get(_DSN_ENV)
    if not dsn:
        print(_MSG_DSN, file=sys.stderr)
        sys.exit(1)
    dsn = dsn.replace("postgresql+asyncpg", "postgresql")
    return await asyncpg.connect(dsn)


async def _find_projects(conn: asyncpg.Connection, project_id: str | None) -> list[asyncpg.Record]:
    if project_id:
        return await conn.fetch(
            "SELECT id, output_dir, image_model, image_style, theme FROM carousel_projects WHERE id = $1",
            project_id,
        )
    return await conn.fetch(
        "SELECT id, output_dir, image_model, image_style, theme FROM carousel_projects WHERE status NOT IN ('pending', 'failed')"
    )


async def _find_slides(conn: asyncpg.Connection, project_id: str) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT id, slide_number, slide_type, image_path, metadata FROM carousel_slides WHERE project_id = $1 ORDER BY slide_number",
        project_id,
    )


async def _existing_generation_keys(conn: asyncpg.Connection, project_id: str) -> set[str]:
    rows = await conn.fetch(
        "SELECT generation_key FROM carousel_image_generations WHERE project_id = $1",
        project_id,
    )
    return {row[_COL_GENERATION_KEY] for row in rows}


def _compute_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_valid_jpeg_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.stat().st_size < _MIN_JPEG_BYTES:
        return False
    try:
        from PIL import Image

        with Image.open(path) as img:
            if img.format != "JPEG":
                return False
            img.verify()
    except Exception:
        return False
    return True


def _resolve_output_dir(project: asyncpg.Record) -> Path | None:
    raw = project[_COL_OUTPUT_DIR]
    if not raw:
        return None
    path = Path(raw).resolve()
    if not path.is_dir():
        return None
    return path


def _resolve_image_path(
    image_path: str | None,
    images_dir: Path,
    slide: asyncpg.Record,
) -> Path | None:
    """Resolve the absolute path to a slide image file."""
    if not image_path:
        return None
    abs_path = Path(image_path).resolve()
    if abs_path.is_file():
        return abs_path
    if images_dir.is_dir():
        candidate = images_dir / f"{_SLIDE_FILENAME_PREFIX}{slide[_COL_SLIDE_NUMBER]}{_SLIDE_IMAGE_EXTENSION}"
        return candidate if candidate.is_file() else None
    return None


async def _process_slide(
    slide: asyncpg.Record,
    ctx: _SlideProcessingContext,
) -> tuple[int, int]:
    """Process a single slide and return (recovered, skipped)."""
    image_path = slide[_COL_IMAGE_PATH]
    if not image_path:
        return 0, 0

    abs_path = _resolve_image_path(image_path, ctx.images_dir, slide)
    if abs_path is None:
        return 0, 1

    if not _is_valid_jpeg_file(abs_path):
        return 0, 1

    generation_key = hashlib.sha256(
        f"{ctx.project[_COL_IMAGE_MODEL]}:{ctx.project[_COL_IMAGE_STYLE]}:{abs_path}".encode()
    ).hexdigest()

    if generation_key in ctx.existing_keys:
        return 0, 1

    content_sha = _compute_sha256(abs_path)

    if ctx.run_mode == RunMode.DRY_RUN:
        print(f"  Would recover: slide {slide[_COL_SLIDE_NUMBER]} from {abs_path.name}")
        return 1, 0

    await ctx.conn.execute(
        """INSERT INTO carousel_image_generations
        (id, project_id, slide_id, slide_number, generation_key, status,
         output_path, content_sha256, provider, model, style, error_json)
        VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NULL)
        ON CONFLICT (generation_key) DO NOTHING""",
        ctx.project[_COL_ID],
        slide[_COL_ID],
        slide[_COL_SLIDE_NUMBER],
        generation_key,
        _STATUS_RECOVERED,
        str(abs_path),
        content_sha,
        ctx.project[_COL_IMAGE_MODEL],
        ctx.project[_COL_IMAGE_MODEL],
        ctx.project[_COL_IMAGE_STYLE],
    )

    return 1, 0


async def _process_project_slides(
    slides: list[asyncpg.Record],
    ctx: _SlideProcessingContext,
) -> tuple[int, int]:
    """Iterate over slides and accumulate recovery stats."""
    recovered = 0
    skipped = 0

    for slide in slides:
        rec, skp = await _process_slide(slide, ctx)
        recovered += rec
        skipped += skp

    return recovered, skipped


async def recover_project(opts: _RecoverProjectOptions) -> tuple[int, int]:
    output_dir = _resolve_output_dir(opts.project)
    if output_dir is None:
        print(f"  Skipping {opts.project[_COL_ID]}: no output_dir or directory not found")
        return 0, 0

    existing_keys = await _existing_generation_keys(opts.conn, opts.project[_COL_ID])
    images_dir = output_dir / _IMAGES_DIR_NAME

    ctx = _SlideProcessingContext(
        conn=opts.conn,
        images_dir=images_dir,
        existing_keys=existing_keys,
        project=opts.project,
        run_mode=opts.run_mode,
    )
    return await _process_project_slides(opts.slides, ctx)


async def report_relative_dirs(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT id, output_dir FROM carousel_projects WHERE output_dir IS NOT NULL AND output_dir NOT LIKE '/%'"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Recover carousel image generation records")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without writing to DB")
    parser.add_argument("--project-id", type=str, default=None, help="Limit to a single project UUID")
    args = parser.parse_args()

    run_mode = RunMode.DRY_RUN if args.dry_run else RunMode.LIVE
    conn = await _get_connection()

    try:
        relatives = await report_relative_dirs(conn)
        if relatives:
            print("Projects with relative output_dir (need normalization):")
            for row in relatives:
                print(f"  {row[_COL_ID]}: {row[_COL_OUTPUT_DIR]}")
            print()

        projects = await _find_projects(conn, args.project_id)
        if not projects:
            print(_MSG_NO_PROJECTS)
            return

        total_recovered = 0
        total_skipped = 0
        for project in projects:
            print(f"Processing project {project[_COL_ID]}...")
            slides = await _find_slides(conn, project[_COL_ID])
            opts = _RecoverProjectOptions(
                conn=conn,
                project=project,
                slides=slides,
                run_mode=run_mode,
            )
            recovered, skipped = await recover_project(opts)
            print(f"  Recovered: {recovered}, Skipped: {skipped}")
            total_recovered += recovered
            total_skipped += skipped

        print(f"\nTotal recovered: {total_recovered}, Total skipped: {total_skipped}")
        if args.dry_run:
            print("(dry run — no changes written)")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
