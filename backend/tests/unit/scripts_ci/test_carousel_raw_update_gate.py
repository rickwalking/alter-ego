"""Rule-fires tests for the carousel raw-UPDATE lint gate (AE-0315, AE-0180).

Feature: tests/features/carousel_run_progress_reaper.feature
The gate bans NEW raw UPDATEs against carousel_projects/carousel_slides
outside the allowlisted, epoch-guarded sites. Per the AE-0180 standard, the
seeded-violation tests prove the rule FIRES — a pass on the real tree alone
proves nothing.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_BACKEND = Path(__file__).resolve().parents[3]
_CHECKER = REPO_BACKEND / "scripts" / "check_carousel_raw_updates.py"
_SRC_ROOT = REPO_BACKEND / "src" / "rag_backend"

_spec = importlib.util.spec_from_file_location("check_carousel_raw_updates", _CHECKER)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("check_carousel_raw_updates", _module)
_spec.loader.exec_module(_module)

scan_for_raw_updates = _module.scan_for_raw_updates
ALLOWED_RAW_UPDATE_FILES = _module.ALLOWED_RAW_UPDATE_FILES

_SEEDED_ORM_VIOLATION = (
    "from sqlalchemy import update\n"
    "stmt = update(CarouselProjectModel).values(phase_status='approved')\n"
)
_SEEDED_TEXTUAL_VIOLATION = (
    "QUERY = \"UPDATE carousel_projects SET phase_status = 'approved'\"\n"
)


class TestCarouselRawUpdateGate:
    # Scenario: gate FIRES on a seeded Core update() against a fenced table
    def test_fires_on_seeded_orm_core_update(self, tmp_path: Path) -> None:
        offender = tmp_path / "new_writer.py"
        offender.write_text(_SEEDED_ORM_VIOLATION, encoding="utf-8")
        violations = scan_for_raw_updates(tmp_path)
        assert len(violations) == 1
        assert "new_writer.py:2" in violations[0]

    # Scenario: gate FIRES on seeded textual SQL against a fenced table
    def test_fires_on_seeded_textual_update(self, tmp_path: Path) -> None:
        offender = tmp_path / "raw_sql.py"
        offender.write_text(_SEEDED_TEXTUAL_VIOLATION, encoding="utf-8")
        violations = scan_for_raw_updates(tmp_path)
        assert len(violations) == 1
        assert "raw_sql.py:1" in violations[0]

    def test_fires_on_slide_table_update(self, tmp_path: Path) -> None:
        offender = tmp_path / "slides.py"
        offender.write_text(
            "stmt = update(CarouselSlideModel).values(body='x')\n", encoding="utf-8"
        )
        assert scan_for_raw_updates(tmp_path)

    def test_allowlisted_file_is_skipped(self, tmp_path: Path) -> None:
        allowed_rel = sorted(ALLOWED_RAW_UPDATE_FILES)[0]
        target = tmp_path / allowed_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_SEEDED_ORM_VIOLATION, encoding="utf-8")
        assert scan_for_raw_updates(tmp_path) == []

    def test_unfenced_tables_are_not_flagged(self, tmp_path: Path) -> None:
        bystander = tmp_path / "other.py"
        bystander.write_text(
            "stmt = update(BlogPostModel).values(title='x')\n"
            "Q = \"UPDATE blog_posts SET title = 'x'\"\n",
            encoding="utf-8",
        )
        assert scan_for_raw_updates(tmp_path) == []

    # Scenario: the real tree carries no un-allowlisted raw UPDATEs
    def test_real_tree_is_clean(self) -> None:
        assert scan_for_raw_updates(_SRC_ROOT) == []

    def test_allowlist_matches_survey_enumeration(self) -> None:
        # The allowlist must stay in lockstep with the write-site survey §2
        # (+ the AE-0320 phase-drift convergence CAS, mirroring the reaper flip).
        assert (
            frozenset({
                "application/services/optimistic_lock_service.py",
                "infrastructure/database/carousel_artifact_build_repository.py",
                "infrastructure/database/carousel_drift_reconciler.py",
                "infrastructure/database/carousel_run_reaper.py",
                "modules/editorial/infrastructure/carousel_run_progress.py",
            })
            == ALLOWED_RAW_UPDATE_FILES
        )
