"""Carousel fields and workflow start of an autopilot run (PR #106 review).

Gherkin: tests/features/autopilot_pov_thesis.feature
("Persona and voice gate", "Slide-1 photo", "Scout POV format" sections)
"""

from __future__ import annotations

from uuid import UUID

import pytest

from rag_backend.modules.autopilot.domain.gate import ProjectSpec
from rag_backend.modules.autopilot.infrastructure.pov_project import (
    policy_version_for,
    pov_fields_for,
    start_input_for,
)
from rag_backend.modules.editorial.public import as_uuid

_PHOTO = "00000000-0000-4000-8000-0000000000aa"


def _spec(**changes: object) -> ProjectSpec:
    base: dict[str, object] = {
        "topic": "T",
        "audience": "Devs",
        "niche": "IA",
        "brief": "b",
        "sources": ("https://x.com/a/status/1",),
        "owner_user_id": "owner-1",
        "persona_id": "persona-pedro",
    }
    base.update(changes)
    return ProjectSpec(**base)  # type: ignore[arg-type]


@pytest.mark.unit
class TestPovFields:
    def test_pov_carries_choice_photo_and_persona(self) -> None:
        spec = _spec(
            content_mode="pov",
            pov_thesis="Tese",
            pov_format="comparacao",
            slide_count=10,
            hook_asset_id=_PHOTO,
        )
        fields = pov_fields_for(spec)
        assert fields["pov_format"] == "comparacao"
        assert fields["slide_count"] == 10
        assert fields["hook_asset_id"] == UUID(_PHOTO)
        assert fields["persona_id"] == "persona-pedro"
        assert policy_version_for(spec) != policy_version_for(_spec())

    def test_pov_without_format_uses_the_default(self) -> None:
        fields = pov_fields_for(_spec(content_mode="pov", pov_thesis="Tese"))
        assert fields["pov_format"] == "opiniao"
        assert fields["hook_asset_id"] is None

    def test_radar_ia_carries_only_the_persona(self) -> None:
        fields = pov_fields_for(_spec(pov_format="opiniao", hook_asset_id=_PHOTO))
        assert fields == {
            "pov_thesis": None,
            "pov_format": None,
            "slide_count": None,
            "hook_asset_id": None,
            "persona_id": "persona-pedro",
        }

    def test_start_input_carries_the_persona_and_sources(self) -> None:
        start = start_input_for(_spec())
        assert start.persona_id == "persona-pedro"
        assert start.user_id == "owner-1"
        assert start.sources[0]["content"] == "https://x.com/a/status/1"

    def test_as_uuid(self) -> None:
        assert as_uuid(None) is None
        assert as_uuid("") is None
        assert as_uuid(_PHOTO) == UUID(_PHOTO)
