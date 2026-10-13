"""Boundary-safe view DTOs. Domain entities stay inside the module."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class AutopilotRunView:
    """Public projection of an autopilot run."""

    run_id: str
    state: str
    state_reason: str | None
