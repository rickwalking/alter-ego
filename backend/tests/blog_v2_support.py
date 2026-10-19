"""Shared ``blog.v2`` content fixtures for blog-post tests (AE-0423, ADR-0025).

``blog_posts.content`` accepts only the ``blog.v2`` document on write, so tests
that create/update/publish posts build their content here. The section id is
fixed so golden snapshots stay deterministic.
"""

from __future__ import annotations

FIXTURE_SECTION_ID = "sec_00000000-0000-4000-8000-000000000001"


def v2_section(
    body: str = "Body",
    heading: str | None = None,
    section_id: str = FIXTURE_SECTION_ID,
) -> dict[str, object]:
    """One section dict as stored in ``content.sections``."""
    return {"id": section_id, "heading": heading, "body_md": body, "image": None}


def v2_content(body: str = "Body", heading: str | None = None) -> dict[str, object]:
    """A minimal, publishable ``blog.v2`` document (one section, no cover)."""
    return {
        "schema": "blog.v2",
        "cover": None,
        "sections": [v2_section(body, heading)],
        "translations": {},
        "quality": None,
    }
