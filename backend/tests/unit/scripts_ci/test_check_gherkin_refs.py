"""Rule-fires regression test for the Gherkin reference ratchet (AE-0446/AE-0180).

Proves the gate FIRES on a seeded scenario no test references (exit 1), accepts
a reference wrapped over two comment lines, tolerates grandfathered scenarios,
and that ``--update-baseline`` refuses to grow the baseline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import scripts.check_gherkin_refs as gate

_FEATURE = """Feature: Seeded
  Scenario: A referenced scenario passes the gate
    Given a test names it
  Scenario: An orphan scenario fails the gate
    Given no test names it
"""

_TEST_WITH_WRAPPED_REF = """
# Scenario: A referenced scenario passes the
#   gate
def test_referenced() -> None: ...
"""


@pytest.fixture
def seeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    features = tmp_path / "backend" / "tests" / "features"
    features.mkdir(parents=True)
    (features / "seeded.feature").write_text(_FEATURE, encoding="utf-8")
    tests = tmp_path / "backend" / "tests" / "unit"
    tests.mkdir(parents=True)
    (tests / "test_seeded.py").write_text(_TEST_WITH_WRAPPED_REF, encoding="utf-8")
    monkeypatch.setattr(gate, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(gate, "_FEATURE_ROOTS", {"backend": features})
    monkeypatch.setattr(
        gate, "_TEST_ROOTS", ((tmp_path / "backend" / "tests", ("*.py",)),)
    )
    monkeypatch.setattr(gate, "_BASELINE", tmp_path / "baseline.json")
    return tmp_path


_ORPHAN = "backend/tests/features/seeded.feature::An orphan scenario fails the gate"


# Scenario: a new scenario without a test reference fails the gate.
def test_gate_fires_on_a_seeded_unreferenced_scenario(
    seeded: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert gate.main(["--scope", "backend"]) == 1
    out = capsys.readouterr().out
    assert _ORPHAN in out
    assert "A referenced scenario passes the gate" not in out.split("gherkin refs")[0]


# Scenario: a grandfathered scenario does not fail the gate.
def test_grandfathered_scenario_passes(seeded: Path) -> None:
    (seeded / "baseline.json").write_text(
        json.dumps({"unreferenced": [_ORPHAN]}), encoding="utf-8"
    )
    assert gate.main(["--scope", "backend"]) == 0


# Scenario: the baseline only shrinks.
def test_update_baseline_refuses_to_grow(seeded: Path) -> None:
    (seeded / "baseline.json").write_text(
        json.dumps({"unreferenced": []}), encoding="utf-8"
    )
    assert gate.main(["--update-baseline"]) == 1
    assert json.loads((seeded / "baseline.json").read_text())["unreferenced"] == []


def test_update_baseline_creates_the_first_baseline(seeded: Path) -> None:
    assert gate.main(["--update-baseline"]) == 0
    stored = json.loads((seeded / "baseline.json").read_text())["unreferenced"]
    assert stored == [_ORPHAN]
