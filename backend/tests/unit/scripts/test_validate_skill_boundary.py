"""Unit tests for skill boundary validation script.

Feature: Skill boundary stays structurally valid (name==folder, runtime/delivery
separation, required slash commands). Delivery skills are intentionally
model-invocable (Skill tool), so `disable-model-invocation` is no longer required
(commit 04a883b6).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.validate_skill_boundary import (
    _validate_delivery_skill_file,
    validate_skill_boundary,
)


@pytest.mark.unit
class TestValidateSkillBoundary:
    """Scenario: Delivery slash commands resolve canonically."""

    def test_skill_boundary_validation_passes(self) -> None:
        errors = validate_skill_boundary()
        assert errors == []

    def test_name_folder_mismatch_is_flagged(self, tmp_path: Path) -> None:
        # Seeded violation: a retained structural check still fires, proving the
        # validator is not a no-op after the disable-model-invocation removal.
        folder = tmp_path / "developer-skill"
        folder.mkdir()
        skill_md = folder / "SKILL.md"
        skill_md.write_text("---\nname: wrong-name\n---\nbody\n", encoding="utf-8")

        errors: list[str] = []
        _validate_delivery_skill_file(skill_md, set(), errors)

        assert any("!= folder" in e for e in errors), errors

    def test_matching_name_folder_passes(self, tmp_path: Path) -> None:
        folder = tmp_path / "developer-skill"
        folder.mkdir()
        skill_md = folder / "SKILL.md"
        skill_md.write_text("---\nname: developer-skill\n---\nbody\n", encoding="utf-8")

        errors: list[str] = []
        _validate_delivery_skill_file(skill_md, set(), errors)

        assert errors == []
