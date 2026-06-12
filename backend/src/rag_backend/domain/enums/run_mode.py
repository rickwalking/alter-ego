"""Run mode enum for distinguishing dry-run vs live execution."""

from __future__ import annotations

from enum import Enum


class RunMode(Enum):
    DRY_RUN = "dry_run"
    LIVE = "live"
