#!/usr/bin/env python3
"""Backfill missing design_tokens fields and subtitle_en for old carousel posts.

Runs directly against the production database.
"""

import asyncio
import json
import os
from pathlib import Path

import asyncpg


async def fix_design_tokens_and_subtitles() -> None:
    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg", "postgresql")
    conn = await asyncpg.connect(dsn)

    rows = await conn.fetch(
        "SELECT id, title, output_dir, design_tokens, blog_translations, subtitle_en FROM carousel_projects WHERE status='completed'"
    )

    for row in rows:
        project_id = row["id"]
        tokens = row["design_tokens"] or {}
        if isinstance(tokens, str):
            tokens = json.loads(tokens) if tokens else {}
        if not isinstance(tokens, dict):
            tokens = {}

        # --- 1. Add rendered_slides_* to design_tokens if missing ---
        images = tokens.get("images", {})
        if not isinstance(images, dict):
            images = {}

        # Determine actual slide count from rendered slide directories
        # Fall back to slides array count, then default to 4
        output_dir = row["output_dir"] or ""
        slide_count = 0
        if output_dir:
            for lang in ("en", "pt"):
                lang_dir = Path(output_dir) / lang
                if lang_dir.exists():
                    slide_files = sorted(lang_dir.glob("slide_*.jpg"))
                    slide_count = max(slide_count, len(slide_files))
        
        if slide_count == 0:
            if "slides" in images and isinstance(images["slides"], list):
                slide_count = len(images["slides"])
            else:
                slide_count = 4

        needs_update = False
        if "rendered_slides_pt" not in images:
            images["rendered_slides_pt"] = [
                f"/api/carousels/{project_id}/slide-images/pt/slide_{i}.jpg"
                for i in range(1, slide_count + 1)
            ]
            needs_update = True
        if "rendered_slides_en" not in images:
            images["rendered_slides_en"] = [
                f"/api/carousels/{project_id}/slide-images/en/slide_{i}.jpg"
                for i in range(1, slide_count + 1)
            ]
            needs_update = True

        if needs_update:
            tokens["images"] = images

        # --- 2. Extract subtitle_en from English blog if missing ---
        subtitle_en = row["subtitle_en"]
        translations = row["blog_translations"] or {}
        if isinstance(translations, str):
            translations = json.loads(translations) if translations else {}

        if not subtitle_en and translations.get("en"):
            en_markdown = translations["en"]
            # Extract first paragraph as subtitle
            lines = en_markdown.strip().split("\n")
            paragraphs = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if stripped:
                    paragraphs.append(stripped)
                elif paragraphs:
                    break
            if paragraphs:
                subtitle_en = " ".join(paragraphs)[:200]
                needs_update = True

        if needs_update:
            await conn.execute(
                """
                UPDATE carousel_projects
                SET design_tokens = $1,
                    subtitle_en = COALESCE($2, subtitle_en)
                WHERE id = $3
                """,
                json.dumps(tokens),
                subtitle_en,
                project_id,
            )
            print(f"  Fixed: {row['title'][:50] if row['title'] else project_id}...")

    await conn.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(fix_design_tokens_and_subtitles())
