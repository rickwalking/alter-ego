"""Unit tests for skill boundary validation script.

Feature: Delivery skills remain slash-only after folder migration
"""

from __future__ import annotations

import pytest
from scripts.validate_skill_boundary import validate_skill_boundary


@pytest.mark.unit
class TestValidateSkillBoundary:
    """Scenario: Delivery slash commands resolve canonically."""

    def test_skill_boundary_validation_passes(self) -> None:
        errors = validate_skill_boundary()
        assert errors == []
