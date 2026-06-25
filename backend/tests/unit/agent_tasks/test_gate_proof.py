"""Rule-fires + coupling tests for the GATES_JSON proof and declared QA mode.

AE-0258 (gate proof) + AE-0260 (declared mode). Per the AE-0180 rule-fires
standard, each new check ships a test proving it FIRES on a seeded violation
(rejects a no-block / fail>0 / no-mode report), not merely that the tree passes.
"""

import shutil
import subprocess  # noqa: S404  # integrity-ok: AE-0258 — the gates.sh↔parser coupling test must run the real bash gate (mirrors test_diff_base.py)
from pathlib import Path

import pytest
from scripts.agent_tasks.constants import STATUS_DEV_COMPLETE, STATUS_REVIEW
from scripts.agent_tasks.gate_proof import evaluate_gate_proof, evaluate_qa_mode
from scripts.agent_tasks.schema import can_transition, parse_ticket

REPO_ROOT = Path(__file__).resolve().parents[4]
# Absolute interpreter so the coupling test never relies on a partial path (S607).
_BASH = shutil.which("bash") or "bash"

# A genuine PASS GATES_JSON line (mirrors scripts/ci/gates.sh print_summary).
_GATES_JSON_PASS = 'GATES_JSON: {"pass":7,"fail":0,"skip":0,"results":[]}'
_GATES_JSON_FAIL = 'GATES_JSON: {"pass":5,"fail":2,"skip":0,"results":[]}'
_GATES_JSON_SKIP = 'GATES_JSON: {"pass":4,"fail":0,"skip":3,"results":[]}'


def _dev_complete_ticket(tmp_path: Path) -> Path:
    content = """# AE-9990 — Test

Status: In Development
Tier: T2

## Goal
g

## Problem
p

## Scope
s

## Non-Goals
n

## Acceptance Criteria
- [x] done

## Test Evidence
```bash
pytest
```
"""
    path = tmp_path / "AE-9990-test.md"
    path.write_text(content, encoding="utf-8")
    return path


def _setup_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setattr("scripts.agent_tasks.schema.REPORTS_DIR", reports)
    return reports


# --- AE-0258 rule-fires: dev-summary GATES_JSON gates Dev Complete ------------
# Scenario: a dev-summary without GATES_JSON cannot reach Dev Complete
def test_dev_complete_blocked_without_gates_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reports = _setup_reports(tmp_path, monkeypatch)
    (reports / "AE-9990.dev-summary.md").write_text(
        "# Dev Summary AE-9990\nAll green, trust me.\n", encoding="utf-8"
    )
    ticket = parse_ticket(_dev_complete_ticket(tmp_path))
    assert ticket is not None
    errors = can_transition(ticket, STATUS_DEV_COMPLETE, enforce_gate_proof=True)
    assert any("GATES_JSON proof" in e for e in errors), errors


def test_dev_complete_passes_with_gates_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reports = _setup_reports(tmp_path, monkeypatch)
    (reports / "AE-9990.dev-summary.md").write_text(
        f"# Dev Summary AE-9990\n{_GATES_JSON_PASS}\n", encoding="utf-8"
    )
    ticket = parse_ticket(_dev_complete_ticket(tmp_path))
    assert ticket is not None
    errors = can_transition(ticket, STATUS_DEV_COMPLETE, enforce_gate_proof=True)
    assert errors == [], errors


# Backward-compat: WITHOUT the flag (the retroactive sweep path) the proof is
# NOT required — grandfathers the 164 pre-existing tickets.
def test_dev_complete_grandfathered_without_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_reports(tmp_path, monkeypatch)
    ticket = parse_ticket(_dev_complete_ticket(tmp_path))
    assert ticket is not None
    errors = can_transition(ticket, STATUS_DEV_COMPLETE)  # default: no enforcement
    assert errors == [], errors


# --- AE-0258 rule-fires: fail>0 blocks; skip>0 warns-but-passes --------------
def test_proof_rejects_fail_gt_zero() -> None:
    outcome = evaluate_gate_proof(
        _written("x.qa.md", f"AE-1 {_GATES_JSON_FAIL}"), "report"
    )
    assert any("fail>0" in e for e in outcome.errors), outcome


def test_proof_warns_on_skip_but_does_not_block() -> None:
    outcome = evaluate_gate_proof(
        _written("y.qa.md", f"AE-1 {_GATES_JSON_SKIP}"), "report"
    )
    assert outcome.errors == [], outcome.errors
    assert any("skip>0" in w for w in outcome.warnings), outcome.warnings


_TMP = Path(__file__).resolve().parent / ".__gateproof_tmp__"


def _written(name: str, body: str) -> Path:
    _TMP.mkdir(exist_ok=True)
    path = _TMP / name
    path.write_text(body, encoding="utf-8")
    return path


def teardown_module(_module: object) -> None:
    for child in _TMP.glob("*"):
        child.unlink()
    if _TMP.exists():
        _TMP.rmdir()


# --- AE-0258 coupling test: a REAL gates.sh line parses ----------------------
# Runs an actual single fast gate and feeds its GATES_JSON line to the parser,
# proving the validator stays coupled to the real script's output format.
def test_real_gates_sh_line_parses(tmp_path: Path) -> None:
    proc = subprocess.run(  # noqa: S603  # integrity-ok: AE-0258 — fixed bash path, fixed gate args, repo-controlled script
        [_BASH, "scripts/ci/gates.sh", "backend:lint", "--changed-only"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    combined = proc.stdout + proc.stderr
    gates_line = next((ln for ln in combined.splitlines() if "GATES_JSON:" in ln), None)
    assert gates_line is not None, f"no GATES_JSON line in real output:\n{combined}"
    report = tmp_path / "real.qa.md"
    report.write_text(f"AE-1\n{gates_line}\n", encoding="utf-8")
    outcome = evaluate_gate_proof(report, "report")
    # A real PASS line parses cleanly (no "no parseable field" error).
    assert not any("no parseable" in e for e in outcome.errors), outcome.errors


# --- AE-0258: wave-report reference satisfies the proof ----------------------
def test_wave_report_reference_satisfies_proof(tmp_path: Path) -> None:
    (tmp_path / "wave-2a.qa.md").write_text(
        f"# Wave 2a\nAE-1\n{_GATES_JSON_PASS}\n", encoding="utf-8"
    )
    per_ticket = tmp_path / "AE-0001.qa.md"
    per_ticket.write_text(
        "# AE-0001\nSee wave-2a.qa.md for the gate proof.\n", encoding="utf-8"
    )
    outcome = evaluate_gate_proof(per_ticket, "report")
    assert outcome.errors == [], outcome.errors


# --- AE-0260 rule-fires: declared QA mode ------------------------------------
def _review_ticket(tmp_path: Path) -> Path:
    path = tmp_path / "AE-9991-test.md"
    path.write_text(
        "# AE-9991 — Test\n\nStatus: Dev Complete\nTier: T2\n\n"
        "## Acceptance Criteria\n- [x] done\n\n## Test Evidence\n```\npytest\n```\n",
        encoding="utf-8",
    )
    return path


def _good_qa(reports: Path) -> None:
    (reports / "AE-9991.dev-summary.md").write_text(
        f"# Dev AE-9991\n{_GATES_JSON_PASS}\n", encoding="utf-8"
    )


# Scenario: a QA report without a declared mode cannot reach Review
def test_review_blocked_without_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reports = _setup_reports(tmp_path, monkeypatch)
    _good_qa(reports)
    (reports / "AE-9991.qa.md").write_text(
        f"# QA AE-9991\n{_GATES_JSON_PASS}\nLooks good.\n", encoding="utf-8"
    )
    ticket = parse_ticket(_review_ticket(tmp_path))
    assert ticket is not None
    errors = can_transition(ticket, STATUS_REVIEW, enforce_gate_proof=True)
    assert any("mode:" in e and "missing" in e.lower() for e in errors), errors


def test_review_blocked_on_invalid_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reports = _setup_reports(tmp_path, monkeypatch)
    _good_qa(reports)
    (reports / "AE-9991.qa.md").write_text(
        f"# QA AE-9991\nmode: vibes\n{_GATES_JSON_PASS}\n", encoding="utf-8"
    )
    ticket = parse_ticket(_review_ticket(tmp_path))
    assert ticket is not None
    errors = can_transition(ticket, STATUS_REVIEW, enforce_gate_proof=True)
    assert any("invalid QA mode" in e for e in errors), errors


def test_review_passes_with_external_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reports = _setup_reports(tmp_path, monkeypatch)
    _good_qa(reports)
    (reports / "AE-9991.qa.md").write_text(
        f"# QA AE-9991\nmode: external\n{_GATES_JSON_PASS}\nReal QA content here.\n",
        encoding="utf-8",
    )
    ticket = parse_ticket(_review_ticket(tmp_path))
    assert ticket is not None
    errors = can_transition(ticket, STATUS_REVIEW, enforce_gate_proof=True)
    assert errors == [], errors


# Scenario: external toolchain down is handled, not blocked
def test_self_fallback_mode_accepted(tmp_path: Path) -> None:
    report = tmp_path / "AE-1.qa.md"
    report.write_text(
        "# QA AE-1\nmode: self-fallback (opencode/codex/cursor all unavailable)\n",
        encoding="utf-8",
    )
    assert evaluate_qa_mode(report, "report") == []
