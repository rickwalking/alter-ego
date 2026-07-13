"""Run-once in-flight presentation-policy upgrade helpers (AE-0312).

Pure, testable core for the deploy-gated migration that bumps non-completed
carousels from v1 to v2 AND re-validates their localized slides under v2, so
casing warnings are visible at whatever step the project is parked on (including
final_review and the publish health card). Bumping the version alone would leave
the STORED v1 report served verbatim — a final_review-parked project would be
approved off a stale report that never checked casing.

The migration is DEPLOY-GATED on AE-0311 (the repair endpoint / "Fix issues"
button). It must NOT run in prod before AE-0311 ships — warnings without a
working fix button would degrade every in-flight review. See
``scripts/upgrade_inflight_presentation_policy_v2.py``.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.presentation_review_pipeline import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY,
    WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY,
    validate_localized_slides,
    validation_report_to_dict,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
)

COMPLETED_STATUS = "completed"


def should_upgrade_project(status: str, current_version: str | None) -> bool:
    """Return True when a project should be upgraded to v2.

    Non-completed projects on any version other than v2 are upgraded. Completed
    projects keep their frozen artifacts and policy version.
    """
    if status == COMPLETED_STATUS:
        return False
    return current_version != PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2


def _slides_from_state(state: dict[str, object]) -> list[dict[str, object]]:
    localized = state.get(WORKFLOW_STATE_LOCALIZED_SLIDES_KEY)
    if not isinstance(localized, list):
        return []
    return [slide for slide in localized if isinstance(slide, dict)]


def build_policy_change_updates(
    state: dict[str, object],
    target_version: str,
) -> dict[str, object]:
    """Re-validate localized slides under ``target_version`` and return updates.

    Returns the workflow-state changes (bumped policy version + fresh
    severity-aware report). Re-validation is pure CPU over already-loaded slide
    data, so it is safe to run in batches during a migration.
    """
    slides = _slides_from_state(state)
    report = validate_localized_slides(slides, policy_version=target_version)
    return {
        WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY: target_version,
        WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: validation_report_to_dict(report),
    }


def build_policy_upgrade_updates(state: dict[str, object]) -> dict[str, object]:
    """Upgrade updates: bump to v2 and re-validate under v2."""
    return build_policy_change_updates(
        state,
        PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
    )


def build_policy_downgrade_updates(state: dict[str, object]) -> dict[str, object]:
    """Downgrade updates: restore v1 and re-validate under v1.

    Re-validating under v1 is deterministic, so it reproduces the prior stored
    v1 report (minus the ``validated_at`` timestamp) without a backup table.
    """
    return build_policy_change_updates(state, DEFAULT_PRESENTATION_POLICY_VERSION)


__all__ = [
    "COMPLETED_STATUS",
    "build_policy_change_updates",
    "build_policy_downgrade_updates",
    "build_policy_upgrade_updates",
    "should_upgrade_project",
]
