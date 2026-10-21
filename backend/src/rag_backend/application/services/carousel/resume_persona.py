"""The project's persona for a background resume.

The resume runner passed ``persona=None`` on every resume, so a content phase
reached through a resume (every autopilot gate approval, and every HTTP
revise) never scored the voice. POV runs then always escalated with
``persona_not_scored``. The project stores the persona it was created with;
the resume now loads it through the editorial facade.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.modules.editorial.public import PovInputsAcl


async def load_project_persona(
    db: AsyncSession, project_id: str
) -> PersonaProfile | None:
    """The persona bound to ``project_id``, or None when it has none."""
    return await PovInputsAcl(db).project_persona(project_id)


__all__ = ["load_project_persona"]
