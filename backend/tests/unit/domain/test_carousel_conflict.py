"""Unit tests for the typed carousel conflict domain model (AE-0316).

Gherkin: tests/features/carousel_typed_conflicts.feature
"""

from rag_backend.domain.constants.carousel_conflicts import (
    CAROUSEL_CONFLICT_CODES,
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
    CONFLICT_CODE_REVISION_CAP_EXCEEDED,
    CONFLICT_CODE_RUN_IN_PROGRESS,
    CONFLICT_CODE_VERSION_CONFLICT,
    CONFLICT_MESSAGES,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_RESUME_ALREADY_IN_PROGRESS,
    ERR_REVISION_CAP_EXCEEDED,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)

UNKNOWN_CODE = "some_future_conflict_code"


class TestCarouselConflictCodes:
    """Scenario: conflict codes stay additive with the legacy detail strings."""

    def test_legacy_codes_reuse_historical_detail_strings(self) -> None:
        assert CONFLICT_CODE_RUN_IN_PROGRESS == ERR_RESUME_ALREADY_IN_PROGRESS
        assert CONFLICT_CODE_VERSION_CONFLICT == ERR_VERSION_CONFLICT
        assert CONFLICT_CODE_REVISION_CAP_EXCEEDED == ERR_REVISION_CAP_EXCEEDED

    def test_all_codes_are_distinct(self) -> None:
        assert len(set(CAROUSEL_CONFLICT_CODES)) == len(CAROUSEL_CONFLICT_CODES)

    def test_every_code_has_a_message(self) -> None:
        for code in CAROUSEL_CONFLICT_CODES:
            assert CONFLICT_MESSAGES[code]


class TestCarouselConflictModel:
    """Scenario: for_code builds canonical conflicts."""

    def test_for_code_uses_canonical_message(self) -> None:
        conflict = CarouselConflict.for_code(CONFLICT_CODE_RUN_IN_PROGRESS)
        assert conflict.code == CONFLICT_CODE_RUN_IN_PROGRESS
        assert conflict.message == CONFLICT_MESSAGES[CONFLICT_CODE_RUN_IN_PROGRESS]
        assert conflict.run_started_at is None
        assert conflict.phase is None

    def test_for_code_unknown_code_falls_back_to_code_as_message(self) -> None:
        conflict = CarouselConflict.for_code(UNKNOWN_CODE)
        assert conflict.message == UNKNOWN_CODE

    def test_for_code_carries_phase_for_cap_conflicts(self) -> None:
        conflict = CarouselConflict.for_code(
            CONFLICT_CODE_REVISION_CAP_EXCEEDED, phase="content"
        )
        assert conflict.phase == "content"

    def test_error_carries_conflict_and_str_is_code(self) -> None:
        conflict = CarouselConflict.for_code(CONFLICT_CODE_MUTATION_IN_PROGRESS)
        error = CarouselConflictError(conflict)
        assert error.conflict is conflict
        assert str(error) == CONFLICT_CODE_MUTATION_IN_PROGRESS
