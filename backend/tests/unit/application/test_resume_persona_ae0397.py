"""The project's persona for a background resume (AE-0397).

Gherkin: tests/features/resume_persona_ae0397.feature
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.carousel.resume_persona import (
    load_project_persona,
)
from rag_backend.domain.models.persona import PersonaProfile

pytestmark = pytest.mark.unit


# Scenario: The project's persona is loaded for the resume
async def test_loads_the_project_persona_through_the_facade() -> None:
    persona = PersonaProfile(name="Pedro")
    db = MagicMock()
    with patch(
        "rag_backend.application.services.carousel.resume_persona.PovInputsAcl"
    ) as acl:
        acl.return_value.project_persona = AsyncMock(return_value=persona)
        result = await load_project_persona(db, "proj")
    acl.assert_called_once_with(db)
    acl.return_value.project_persona.assert_awaited_once_with("proj")
    assert result is persona
