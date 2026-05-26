"""Unit tests for domain complexity metrics."""

import pytest

from rag_backend.domain.metrics import (
    COMPLEXITY_THRESHOLDS,
    MAX_COMPLEXITY,
    ComplexityViolationError,
)


@pytest.mark.unit
class TestComplexityViolationError:
    """Tests for ComplexityViolationError reporting."""

    def test_message_includes_violation_details(self) -> None:
        """Given violations, when raised, then message lists thresholds exceeded."""
        error = ComplexityViolationError([
            {"type": "complexity", "actual": 12},
            {"type": "branches", "actual": 8},
        ])

        assert error.violations[0]["type"] == "complexity"
        assert "Complexity complexity = 12 >" in error.message
        assert str(MAX_COMPLEXITY) in error.message
        assert "Complexity branches = 8 >" in error.message

    def test_unknown_violation_type_uses_zero_threshold(self) -> None:
        """Given unknown metric type, when raised, then threshold defaults to zero."""
        error = ComplexityViolationError([{"type": "unknown_metric", "actual": 3}])

        assert "Complexity unknown_metric = 3 > 0" in error.message

    def test_complexity_thresholds_expose_all_limits(self) -> None:
        """Given module constants, when accessed, then all thresholds are defined."""
        assert COMPLEXITY_THRESHOLDS["complexity"] == MAX_COMPLEXITY
        assert COMPLEXITY_THRESHOLDS["nested"] == 3
