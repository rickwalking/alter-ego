"""Rule-fires tests for the backend jscpd duplication gate.

Feature: backend:duplication blocks copy-paste in Python source
  Scenario: two files share a 30-line identical function -> non-zero exit
  Scenario: two files hold distinct code                  -> zero exit
  Scenario: module facade files mirror each other         -> excluded, zero exit
  Scenario: jscpd binary is missing                       -> gate SKIPs (77)
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
JSCPD = REPO_ROOT / "frontend" / "node_modules" / ".bin" / "jscpd"
BASH = shutil.which("bash") or "bash"
SEEDED_LINES = 30
EXIT_SKIP = 77


def _function(name: str, salt: str) -> str:
    lines = [f"def {name}(values: list[int]) -> int:"]
    lines.append("    total = 0")
    for index in range(SEEDED_LINES - 3):
        lines.append(
            f"    total += values[{index}] * {index + 2} + len('{salt}{index}')"
        )
    lines.append("    return total")
    return "\n".join(lines) + "\n"


def _scan(source_dir: Path) -> subprocess.CompletedProcess[str]:
    assert JSCPD.exists(), (
        f"jscpd binary missing at {JSCPD}: run `cd frontend && npm ci` "
        "(the backend duplication gate reuses the frontend devDependency)"
    )
    return subprocess.run(  # noqa: S603  # integrity-ok: fixed binary path, test-controlled arguments
        [str(JSCPD), str(source_dir), "--config", str(CONFIG)],
        cwd=source_dir.parent,
        capture_output=True,
        text=True,
        check=False,
    )


# Scenario: two files share a 30-line identical function -> non-zero exit
def test_identical_function_in_two_files_fails_the_gate(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    shared = _function("compute", "same")
    (src / "first.py").write_text(shared, encoding="utf-8")
    (src / "second.py").write_text(shared, encoding="utf-8")

    result = _scan(src)

    assert result.returncode != 0, result.stdout + result.stderr
    assert "Found 1 clones" in result.stdout


# Scenario: two files hold distinct code -> zero exit
def test_distinct_code_passes_the_gate(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "first.py").write_text(_function("alpha", "one"), encoding="utf-8")
    (src / "second.py").write_text(
        "def beta(text: str) -> str:\n    return text.strip().lower()\n",
        encoding="utf-8",
    )

    result = _scan(src)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Found 0 clones" in result.stdout


# Scenario: module facade files mirror each other -> excluded, zero exit
def test_module_facade_files_are_excluded(tmp_path: Path) -> None:
    src = tmp_path / "src" / "pkg" / "modules" / "billing"
    src.mkdir(parents=True)
    shared = _function("compute", "same")
    (src / "__init__.py").write_text(shared, encoding="utf-8")
    (src / "public.py").write_text(shared, encoding="utf-8")

    result = _scan(tmp_path / "src")

    assert result.returncode == 0, result.stdout + result.stderr


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
