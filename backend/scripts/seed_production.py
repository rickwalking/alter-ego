#!/usr/bin/env python3
"""Seed production database with carousel projects and slides from local runs."""

import asyncio
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

SEED_FILE = "/opt/alter-ego/seed/carousel_seed_final.json"
OWNER_ID = "25c56d3c-a9b9-41df-ad1c-9084ea5a97e7"  # Admin user ID
OUTPUT_BASE = "/app/output/carousels"

# Map old carousel IDs to new stable IDs if needed (keep same for consistency)
ID_MAP = {}


def now() -> datetime:
    return datetime.now(UTC)


async def seed_database():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")

    conn = await asyncpg.connect(database_url)

    try:
        # 1. Ensure admin user exists
        user_exists = await conn.fetchval(
            "SELECT 1 FROM users WHERE id = $1", OWNER_ID
        )
        if not user_exists:
            print(f"Creating admin user {OWNER_ID}...")
            await conn.execute(
                """
                INSERT INTO users (id, email, full_name, hashed_password, role, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
                ON CONFLICT (id) DO NOTHING
                """,
                OWNER_ID,
                "admin@alterego.app",
                "System Administrator",
                "$2b$12$dummy_hash_for_admin_user_created_by_seed_script",
                "admin",
                True,
                now(),
            )

        # 2. Load seed data
        with open(SEED_FILE, encoding="utf-8") as f:
            projects = json.load(f)

        print(f"Seeding {len(projects)} carousel projects...")

        for proj in projects:
            proj_id = proj["id"]
            output_dir = f"{OUTPUT_BASE}/{proj_id}"

            # Check if project already exists
            existing = await conn.fetchval(
                "SELECT 1 FROM carousel_projects WHERE id = $1", proj_id
            )
            if existing:
                print(f"  Skipping existing project: {proj['title'][:50]}...")
                continue

            # Determine language
            lang = proj.get("language", "pt")

            # Build blog translations
            blog_translations = {}
            if lang == "pt":
                blog_translations = {"pt": proj["blog_markdown"], "en": None}
            else:
                blog_translations = {"en": proj["blog_markdown"], "pt": None}

            # Insert project
            await conn.execute(
                """
                INSERT INTO carousel_projects (
                    id, owner_id, is_public, topic, audience, niche, title, subtitle,
                    slides_config, aspect_ratio, language, generate_images, image_model,
                    image_style, theme, primary_color, accent_color, background_color,
                    blog_markdown, blog_translations, caption, linkedin_post_pt, linkedin_post_en,
                    design_tokens, status, error_message, output_dir, pdf_path, pdf_path_en,
                    phase_progress, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8,
                    $9, $10, $11, $12, $13,
                    $14, $15, $16, $17, $18,
                    $19, $20, $21, $22, $23,
                    $24, $25, $26, $27, $28, $29,
                    $30, $31, $31
                )
                """,
                proj_id,
                OWNER_ID,
                True,  # is_public
                proj["topic"],
                "Software developers, AI enthusiasts, tech investors",  # audience
                "Tech",  # niche
                proj["title"],
                proj.get("subtitle", ""),
                f"{proj['slide_count']}_slides",  # slides_config
                "4:5",  # aspect_ratio
                lang,
                1,  # generate_images
                "gemini-2.5-flash-preview-05-20",  # image_model
                "neon_comic",  # image_style
                "auto",  # theme
                "#0ac5a8",  # primary_color
                "#8b5cf6",  # accent_color
                "#080c12",  # background_color
                proj["blog_markdown"],
                json.dumps(blog_translations),
                proj.get("caption", "")[:2000],
                "",  # linkedin_post_pt
                "",  # linkedin_post_en
                json.dumps({}),
                "completed",  # status
                None,  # error_message
                output_dir,
                None,  # pdf_path
                None,  # pdf_path_en
                json.dumps({"completed": True, "current_phase": "completed"}),
                now(),
            )

            # Insert slides
            for slide in proj.get("slides", []):
                slide_id = str(uuid.uuid4())
                slide_num = slide["slide_number"]

                # Determine image path
                # Try pt/en/images subdirs first, then root
                image_path = None
                for sub in [lang, "images", ""]:
                    check_dir = Path(output_dir) / sub if sub else Path(output_dir)
                    candidate = check_dir / f"slide_{slide_num}.jpg"
                    if candidate.exists():
                        image_path = str(candidate)
                        break

                await conn.execute(
                    """
                    INSERT INTO carousel_slides (
                        id, project_id, slide_number, slide_type, heading, body,
                        html_content, image_path, image_prompt, metadata, extras, created_at, updated_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6,
                        $7, $8, $9, $10, $11, $12, $12
                    )
                    """,
                    slide_id,
                    proj_id,
                    slide_num,
                    "content",  # slide_type
                    slide.get("heading", ""),
                    slide.get("body", ""),
                    "",  # html_content
                    image_path,
                    "",  # image_prompt
                    json.dumps({}),
                    json.dumps({}),
                    now(),
                )

            print(f"  Inserted: {proj['title'][:50]}... ({proj['slide_count']} slides)")

        # 3. Verify
        project_count = await conn.fetchval("SELECT COUNT(*) FROM carousel_projects")
        slide_count = await conn.fetchval("SELECT COUNT(*) FROM carousel_slides")
        print(f"\nDone! Total projects: {project_count}, Total slides: {slide_count}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
