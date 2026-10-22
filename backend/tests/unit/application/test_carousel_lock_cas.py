"""Optimistic lock-version compare-and-swap shared by the carousel edit services.

Scenario: a clean bump returns without raising.
Scenario: a lost race raises a version-conflict 409 error.
Scenario: any other ValueError propagates unchanged.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.carousel import carousel_lock_cas
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_VERSION_CONFLICT,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models.carousel_conflict import CarouselConflictError

_OWNER = "rag_backend.application.services.carousel.carousel_lock_cas.CarouselProjectWriteOwner"


def _owner(side_effect: BaseException | None) -> MagicMock:
    owner = MagicMock()
    owner.return_value.bump_resume_lock_version = AsyncMock(side_effect=side_effect)
    return owner


# Scenario: a clean bump returns without raising.
async def test_clean_bump_passes_project_and_version() -> None:
    owner = _owner(None)
    db = MagicMock()
    with patch(_OWNER, owner):
        await carousel_lock_cas.take_lock_version_cas(db, "project-1", 4)

    owner.assert_called_once_with(db)
    owner.return_value.bump_resume_lock_version.assert_awaited_once_with("project-1", 4)


# Scenario: a lost race raises a version-conflict 409 error.
async def test_lost_race_raises_version_conflict() -> None:
    with (
        patch(_OWNER, _owner(ValueError(ERR_VERSION_CONFLICT))),
        pytest.raises(CarouselConflictError) as raised,
    ):
        await carousel_lock_cas.take_lock_version_cas(MagicMock(), "project-1", 4)

    assert raised.value.conflict.code == CONFLICT_CODE_VERSION_CONFLICT


# Scenario: any other ValueError propagates unchanged.
async def test_other_value_error_propagates() -> None:
    with (
        patch(_OWNER, _owner(ValueError("boom"))),
        pytest.raises(ValueError, match="boom"),
    ):
        await carousel_lock_cas.take_lock_version_cas(MagicMock(), "project-1", 4)
