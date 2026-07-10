"""Unit tests for the resume-start artifact-mutation guard (AE-0316).

Gherkin: tests/features/carousel_typed_conflicts.feature
  Scenario: Resume is refused while an artifact mutator holds the lock
"""

from unittest.mock import AsyncMock, patch

import pytest

from rag_backend.api.routes.carousels.editorial_workflow_routes_validate import (
    ensure_no_artifact_mutation_in_progress,
)
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
)
from rag_backend.domain.models.carousel_conflict import CarouselConflictError

PROJECT_ID = "66014ba3-2c50-48f2-b4b9-cbc241e07caf"
_GUARD_TARGET = (
    "rag_backend.api.routes.carousels.editorial_workflow_routes_validate"
    ".is_carousel_project_lock_held_session"
)


class TestEnsureNoArtifactMutationInProgress:
    async def test_passes_when_lock_not_held(self) -> None:
        with patch(_GUARD_TARGET, new=AsyncMock(return_value=False)):
            await ensure_no_artifact_mutation_in_progress(
                AsyncMock(), PROJECT_ID
            )

    async def test_raises_typed_conflict_when_lock_held(self) -> None:
        with patch(_GUARD_TARGET, new=AsyncMock(return_value=True)):
            with pytest.raises(CarouselConflictError) as exc_info:
                await ensure_no_artifact_mutation_in_progress(
                    AsyncMock(), PROJECT_ID
                )
        assert exc_info.value.conflict.code == CONFLICT_CODE_MUTATION_IN_PROGRESS
