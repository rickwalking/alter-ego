"""``AUTOPILOT_START_SPACING_MINUTES`` reaches the runner the worker builds.

Feature: backend/tests/features/carousel_generation_load_ae0520.feature
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.bootstrap.autopilot_worker_factory import autopilot_tick_config
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.modules.autopilot.bootstrap import runner_dependencies
from rag_backend.modules.autopilot.infrastructure.start_history import (
    SqlStartHistory,
)


def _settings(**overrides: object) -> Settings:
    return Settings(credentials_encryption_key="", **overrides)


@pytest.mark.unit
async def test_worker_passes_the_setting_to_the_runner(
    db_session: AsyncSession,
) -> None:
    """Scenario: The runner uses the configured start spacing."""
    config = autopilot_tick_config(
        _settings(autopilot_start_spacing_minutes=7), MagicMock()
    )
    assert config.start_spacing_minutes == 7

    spacing = runner_dependencies(db_session, config).spacing

    assert spacing is not None
    assert spacing.minimum == timedelta(minutes=7)
    assert isinstance(spacing.starts, SqlStartHistory)


@pytest.mark.unit
def test_negative_spacing_is_rejected() -> None:
    """Scenario: A negative start spacing is rejected."""
    with pytest.raises(ValidationError):
        _settings(autopilot_start_spacing_minutes=-1)
