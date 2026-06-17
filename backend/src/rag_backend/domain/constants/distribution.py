"""Domain constants + contracts for the canonical distribution home (AE-0204).

The Instagram caption + LinkedIn posts of a carousel-derived item have a single
canonical home — the ``blog_posts.distribution`` JSONB column. This module owns the
field-name constants (the single source of these keys, shared by the infrastructure
accessor, every reader, and the migration) and the read-port Protocol so the
application layer can depend on a distribution reader contract WITHOUT importing the
infrastructure accessor (ADR-009 layering).
"""

from __future__ import annotations

from typing import Protocol

# Canonical ``blog_posts.distribution`` JSON keys — the single source of these
# field names for the infrastructure accessor, every reader, and the backfill.
DISTRIBUTION_CAPTION_KEY = "caption"
DISTRIBUTION_LINKEDIN_POST_PT_KEY = "linkedin_post_pt"
DISTRIBUTION_LINKEDIN_POST_EN_KEY = "linkedin_post_en"

DISTRIBUTION_KEYS: tuple[str, str, str] = (
    DISTRIBUTION_CAPTION_KEY,
    DISTRIBUTION_LINKEDIN_POST_PT_KEY,
    DISTRIBUTION_LINKEDIN_POST_EN_KEY,
)


class DistributionReader(Protocol):
    """Reads the canonical distribution payload for a carousel project.

    The application layer depends on this contract; the concrete reader (the
    infrastructure ``read_distribution`` accessor over ``blog_posts.distribution``)
    is injected at the inbound edge (API/worker), so the application layer never
    imports the infrastructure accessor directly.
    """

    async def __call__(self, project_id: str) -> dict[str, str | None] | None:
        """Return ``{caption, linkedin_post_pt, linkedin_post_en}`` or ``None``."""
        ...


__all__ = [
    "DISTRIBUTION_CAPTION_KEY",
    "DISTRIBUTION_KEYS",
    "DISTRIBUTION_LINKEDIN_POST_EN_KEY",
    "DISTRIBUTION_LINKEDIN_POST_PT_KEY",
    "DistributionReader",
]
