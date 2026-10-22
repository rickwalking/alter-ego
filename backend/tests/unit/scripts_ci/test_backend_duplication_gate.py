"""Backend jscpd duplication gate: config ratchet and the missing-tool SKIP.

The rule-fires tests that run jscpd on seeded Python (a 30-line clone fails,
distinct code and the module facades pass) live in
frontend/src/scripts/backend-duplication-gate.test.ts, next to the jscpd binary
the gate reuses; the backend test job does not install frontend packages.

Feature: backend:duplication blocks copy-paste in Python source
  Scenario: jscpd binary is missing -> gate SKIPs (77)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # noqa: S404  # integrity-ok: a test for a jscpd gate must invoke the binary (mirrors test_require_tool.py)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG = REPO_ROOT / "backend" / ".jscpd.json"
GATES = REPO_ROOT / "scripts" / "ci" / "gates.sh"
BASH = shutil.which("bash") or "bash"


def test_config_threshold_is_a_ratchet_below_the_pre_cleanup_baseline() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))

    assert config["format"] == ["python"]
    assert config["gitignore"] is True
    assert 0 < config["threshold"] < 1.08


# Scenario: jscpd binary is missing -> gate SKIPs (77)
def test_gate_skips_when_jscpd_is_hidden(tmp_path: Path) -> None:
    env = {**os.environ, "FRONTEND_BIN_DIR": str(tmp_path)}
    env.pop("GATES_REQUIRE_ALL", None)

    result = subprocess.run(  # noqa: S603  # integrity-ok: fixed bash path, test-controlled script
        [BASH, str(GATES), "backend:duplication"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert ">>> backend:duplication: SKIP" in result.stdout, result.stdout
    assert "jscpd" in result.stderr
