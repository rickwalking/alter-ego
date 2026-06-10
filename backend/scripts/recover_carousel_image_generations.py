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
from pathlib import Path

import asyncpg

_DSN_ENV = "DATABASE_URL"
_STATUS_SUCCEEDED = "succeeded"
_STATUS_RECOVERED = "recovered"
_STATUS_FAILED = "failed"
_DIR_CAROUSELS = "output/carousels"
_MSG_DSN = "Set DATABASE_URL environment variable"
_MSG_NO_PROJECTS = "No carousel projects found to process"


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
    return {row["generation_key"] for row in rows}


def _compute_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_valid_jpeg_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.stat().st_size < 1024:
        return False
    try:
        from PIL import Image

        with Image.open(path) as img:
            if img.format != "JPEG":
                return False
            img.verify()
        return True
    except Exception:
        return False


def _resolve_output_dir(project: asyncpg.Record) -> Path | None:
    raw = project["output_dir"]
    if not raw:
        return None
    path = Path(raw).resolve()
    if not path.is_dir():
        return None
    return path


async def recover_project(
    conn: asyncpg.Connection,
    project: asyncpg.Record,
    slides: list[asyncpg.Record],
    dry_run: bool,
) -> tuple[int, int]:
    output_dir = _resolve_output_dir(project)
    if output_dir is None:
        print(f"  Skipping {project['id']}: no output_dir or directory not found")
        return 0, 0

    existing_keys = await _existing_generation_keys(conn, project["id"])
    images_dir = output_dir / "images"
    recovered = 0
    skipped = 0

    for slide in slides:
        image_path = slide["image_path"]
        if not image_path:
            continue

        abs_path = Path(image_path).resolve() if image_path else None
        if abs_path is None or not abs_path.is_file():
            if images_dir.is_dir():
                candidate = images_dir / f"slide_{slide['slide_number']}.jpg"
                if candidate.is_file():
                    abs_path = candidate
                else:
                    skipped += 1
                    continue
            else:
                skipped += 1
                continue

        if not _is_valid_jpeg_file(abs_path):
            skipped += 1
            continue

        generation_key = hashlib.sha256(
            f"{project['image_model']}:{project['image_style']}:{abs_path}".encode()
        ).hexdigest()

        if generation_key in existing_keys:
            skipped += 1
            continue

        content_sha = _compute_sha256(abs_path)
        metadata = slide["metadata"] or {}

        if dry_run:
            print(f"  Would recover: slide {slide['slide_number']} from {abs_path.name}")
        else:
            await conn.execute(
                """INSERT INTO carousel_image_generations
                (id, project_id, slide_id, slide_number, generation_key, status,
                 output_path, content_sha256, provider, model, style, error_json)
                VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NULL)
                ON CONFLICT (generation_key) DO NOTHING""",
                project["id"],
                slide["id"],
                slide["slide_number"],
                generation_key,
                _STATUS_RECOVERED,
                str(abs_path),
                content_sha,
                project["image_model"],
                project["image_model"],
                project["image_style"],
            )

        recovered += 1
        existing_keys.add(generation_key)

    return recovered, skipped


async def report_relative_dirs(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT id, output_dir FROM carousel_projects WHERE output_dir IS NOT NULL AND output_dir NOT LIKE '/%'"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Recover carousel image generation records")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without writing to DB")
    parser.add_argument("--project-id", type=str, default=None, help="Limit to a single project UUID")
    args = parser.parse_args()

    conn = await _get_connection()

    try:
        relatives = await report_relative_dirs(conn)
        if relatives:
            print("Projects with relative output_dir (need normalization):")
            for row in relatives:
                print(f"  {row['id']}: {row['output_dir']}")
            print()

        projects = await _find_projects(conn, args.project_id)
        if not projects:
            print(_MSG_NO_PROJECTS)
            return

        total_recovered = 0
        total_skipped = 0
        for project in projects:
            print(f"Processing project {project['id']}...")
            slides = await _find_slides(conn, project["id"])
            recovered, skipped = await recover_project(conn, project, slides, args.dry_run)
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