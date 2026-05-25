"""Complexity metrics and analysis for code quality.

Provides thresholds and measurement utilities for enforcing code complexity
limits across the codebase.
"""

from __future__ import annotations

from typing import Any

# Maximum allowed complexity metrics (industry standard)
MAX_COMPLEXITY = 10
MAX_BRANCHES = 6
MAX_STATEMENTS = 40
MAX_ARGS = 5
MAX_RETURNS = 3
MAX_LOCALS = 10
MAX_NESTED = 3

# Mapping of metric names to their thresholds
COMPLEXITY_THRESHOLDS: dict[str, int] = {
    "complexity": MAX_COMPLEXITY,
    "branches": MAX_BRANCHES,
    "statements": MAX_STATEMENTS,
    "args": MAX_ARGS,
    "returns": MAX_RETURNS,
    "locals": MAX_LOCALS,
    "nested": MAX_NESTED,
}


class ComplexityViolationError(Exception):
    """Raised when complexity metrics exceed thresholds."""

    def __init__(self, violations: list[dict[str, Any]]) -> None:
        self.violations = violations
        self.message = self._generate_message()

    def _generate_message(self) -> str:
        messages: list[str] = []
        for violation in self.violations:
            vtype = violation.get("type", "unknown")
            actual = violation.get("actual", 0)
            threshold = COMPLEXITY_THRESHOLDS.get(vtype, 0)
            messages.append(f"Complexity {vtype} = {actual} > {threshold}")
        return f"Complexity violations: {'; '.join(messages)}"


__all__ = [
    "COMPLEXITY_THRESHOLDS",
    "MAX_ARGS",
    "MAX_BRANCHES",
    "MAX_COMPLEXITY",
    "MAX_LOCALS",
    "MAX_NESTED",
    "MAX_RETURNS",
    "MAX_STATEMENTS",
    "ComplexityViolationError",
]
