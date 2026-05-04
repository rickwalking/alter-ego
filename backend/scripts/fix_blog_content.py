#!/usr/bin/env python3
"""Fix broken blog content and backfill missing fields for old carousel posts.

Runs directly against the production database.  Fixes:

1. Adds title_en / subtitle_en columns if missing
2. Backfills title_en / subtitle_en from English blog translations
3. Backfills design_tokens.layout.badge_label from project.niche
4. Cleans up blog_markdown and blog_translations["en"]:
   - Strips leading H1 (prevents duplicate title)
   - Removes backtick-wrapped duplicate paragraphs
   - Strips HTML fragment artifacts
   - Collapses excessive whitespace
"""

import asyncio
import json
import os
import re

import asyncpg


def _strip_leading_h1(markdown: str) -> str:
    """Remove the first '# Title' or '# Title: Subtitle' line."""
    lines = markdown.split("\n")
    if not lines:
        return markdown
    first = lines[0].strip()
    if first.startswith("# "):
        # Skip the H1 line and any immediately following blank lines
        idx = 1
        while idx < len(lines) and lines[idx].strip() == "":
            idx += 1
        return "\n".join(lines[idx:])
    return markdown


def _remove_backtick_duplicates(text: str) -> str:
    """Remove lines wrapped in backticks that are immediately duplicated as normal text."""
    lines = text.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Check if this line is a backtick-wrapped paragraph (not inline code inside text)
        if (
            stripped.startswith("`")
            and stripped.endswith("`")
            and stripped.count("`") == 2
            and i + 1 < len(lines)
        ):
            inner = stripped[1:-1].strip()
            next_line = lines[i + 1].strip()
            # If next line is the same text without backticks, skip the backtick line
            if inner == next_line:
                i += 1
                continue
        result.append(line)
        i += 1
    return "\n".join(result)


def _strip_html_fragments(text: str) -> str:
    """Remove common HTML fragment artifacts like unclosed tags."""
    # Remove standalone `" />` at end of lines
    text = re.sub(r'"\s*/?>\s*$', "", text, flags=re.MULTILINE)
    # Remove empty image tags
    text = re.sub(r'<img\s+[^>]*?/>', "", text, flags=re.IGNORECASE)
    # Remove other unclosed/common HTML tags
    text = re.sub(r'<\w+[^>]*?>', "", text)
    text = re.sub(r'</\w+>', "", text)
    return text


def _collapse_whitespace(text: str) -> str:
    """Collapse more than 2 consecutive blank lines to 2."""
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def _remove_indented_duplicates(text: str) -> str:
    """Remove lines with 4+ spaces of indentation that duplicate a nearby heading.

    In Markdown, 4+ spaces creates a code block. Old generation templates
    produced indented duplicate lines after headings that render as unwanted
    <code> blocks.
    """
    lines = text.split("\n")
    result: list[str] = []
    recent_headings: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            recent_headings.add(stripped[3:].strip().lower())
        elif stripped.startswith("# "):
            recent_headings.add(stripped[2:].strip().lower())
        # Skip indented lines (4+ leading spaces) that are contained in a recent heading
        if line.startswith("    ") and stripped:
            lowered = stripped.lower()
            if any(lowered in h or h in lowered for h in recent_headings):
                continue
        result.append(line)
    return "\n".join(result)


def _remove_duplicate_paragraphs(text: str) -> str:
    """Remove duplicate paragraphs, even when separated by blank lines."""
    lines = text.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        result.append(line)
        if line.strip():
            j = i + 1
            # Skip blank lines
            while j < len(lines) and not lines[j].strip():
                j += 1
            # If next non-empty line is identical, skip it (and the blank lines between)
            if j < len(lines) and lines[j].strip() == line.strip():
                i = j + 1
                continue
        i += 1
    return "\n".join(result)


def _remove_indented_emoji_lines(text: str) -> str:
    """Remove indented lines that contain only emojis/symbols (common LLM artifacts)."""
    lines = text.split("\n")
    result: list[str] = []
    for line in lines:
        if line.startswith("    "):
            stripped = line.strip()
            # Skip if stripped content has no letters or digits (only emojis/symbols)
            if stripped and not any(c.isalnum() for c in stripped):
                continue
        result.append(line)
    return "\n".join(result)


def _remove_indented_paragraph_duplicates(text: str) -> str:
    """Remove indented lines that duplicate the following non-indented paragraph."""
    lines = text.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("    ") and i + 1 < len(lines):
            stripped = line.strip()
            next_line = lines[i + 1].strip()
            if stripped and next_line and (stripped in next_line or next_line in stripped):
                i += 1
                continue
        result.append(line)
        i += 1
    return "\n".join(result)


def _extract_title_and_subtitle(markdown: str) -> tuple[str | None, str | None]:
    """Extract title and subtitle from markdown first heading."""
    lines = markdown.strip().split("\n")
    if not lines:
        return None, None
    first_line = lines[0]
    if not first_line.startswith("# "):
        return None, None
    heading = first_line[2:].strip()
    if ":" in heading:
        separator_pos = heading.index(":")
        title = heading[:separator_pos].strip()
        subtitle = heading[separator_pos + 1 :].strip()
        return title, subtitle
    return heading, None


def cleanup_markdown(raw: str) -> str:
    """Run full cleanup pipeline on blog markdown."""
    text = raw
    text = _strip_leading_h1(text)
    text = _remove_backtick_duplicates(text)
    text = _remove_indented_duplicates(text)
    text = _remove_indented_emoji_lines(text)
    text = _remove_indented_paragraph_duplicates(text)
    text = _remove_duplicate_paragraphs(text)
    text = _strip_html_fragments(text)
    text = _collapse_whitespace(text)
    return text


async def fix_blogs() -> None:
    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg", "postgresql")
    conn = await asyncpg.connect(dsn)

    # 1. Ensure columns exist
    try:
        await conn.execute(
            "ALTER TABLE carousel_projects ADD COLUMN IF NOT EXISTS title_en VARCHAR(500)"
        )
        await conn.execute(
            "ALTER TABLE carousel_projects ADD COLUMN IF NOT EXISTS subtitle_en TEXT"
        )
        print("Columns added (or already existed).")
    except Exception as exc:
        print(f"Warning adding columns: {exc}")

    rows = await conn.fetch(
        "SELECT id, title, niche, blog_markdown, blog_translations, design_tokens FROM carousel_projects WHERE status='completed'"
    )

    for row in rows:
        project_id = row["id"]
        niche = row["niche"] or "CARROSSEL"
        translations = row["blog_translations"] or {}
        if isinstance(translations, str):
            translations = json.loads(translations)

        # --- 1. Backfill title_en / subtitle_en from English translation ---
        title_en = None
        subtitle_en = None
        en_markdown = translations.get("en")
        if en_markdown:
            t, s = _extract_title_and_subtitle(en_markdown)
            title_en = t
            subtitle_en = s

        # --- 2. Cleanup PT markdown ---
        pt_raw = row["blog_markdown"] or ""
        pt_clean = cleanup_markdown(pt_raw)

        # --- 3. Cleanup EN markdown ---
        en_markdown = translations.get("en")
        en_clean = None
        if en_markdown:
            en_clean = cleanup_markdown(en_markdown)

        # --- 4. Fix missing blog_markdown ---
        # If blog_markdown is empty but a translation exists, copy it back
        if not pt_clean:
            if translations.get("pt"):
                pt_clean = cleanup_markdown(translations["pt"])
            elif translations.get("en"):
                pt_clean = cleanup_markdown(translations["en"])

        # --- 5. Update translations ---
        new_translations = dict(translations)
        pt_changed = pt_clean is not None and pt_clean != (row["blog_markdown"] or "")
        en_changed = en_clean is not None and en_clean != en_markdown
        if pt_changed:
            new_translations["pt"] = pt_clean
        if en_changed:
            new_translations["en"] = en_clean
        # Remove empty string translations
        for key in list(new_translations.keys()):
            if new_translations[key] == "":
                del new_translations[key]

        # --- 5. Update badge_label in design_tokens ---
        tokens = row["design_tokens"] or {}
        if isinstance(tokens, str):
            tokens = json.loads(tokens) if tokens else {}
        if not isinstance(tokens, dict):
            tokens = {}

        layout = tokens.get("layout", {})
        if not isinstance(layout, dict):
            layout = {}
        layout["badge_label"] = niche.strip()
        tokens["layout"] = layout

        # --- 6. Persist everything ---
        await conn.execute(
            """
            UPDATE carousel_projects
            SET title_en = COALESCE($1, title_en),
                subtitle_en = COALESCE($2, subtitle_en),
                blog_markdown = $3,
                blog_translations = $4,
                design_tokens = $5
            WHERE id = $6
            """,
            title_en,
            subtitle_en,
            pt_clean,
            json.dumps(new_translations) if new_translations else None,
            json.dumps(tokens),
            project_id,
        )

        print(f"  Fixed: {row['title'][:50] if row['title'] else project_id}...")

    await conn.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(fix_blogs())
