"""Rule-fires tests for scripts/ci/check_autopilot_env_parity.py (AE-0359, AE-0180).

The checker fails CI when deploy.yml and docker-compose.prod.yml disagree on
an autopilot variable, or when AUTOPILOT_ENABLED does not default to false.
A clean-tree pass is not enough: these tests prove a seeded violation exits 1.

AE-0153: CI/config ticket. No .feature file. The worker skip when the flag is
false is already covered by test_run_tick_skips_autopilot_when_disabled.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess  # noqa: S404  # integrity-ok: AE-0359 — a CLI checker test must invoke a subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CHECKER = REPO_ROOT / "scripts" / "ci" / "check_autopilot_env_parity.py"
PYTHON = shutil.which("python3") or sys.executable

EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_USAGE = 2

_TICKET_ENV_NAMES = (
    "META_IG_ACCESS_TOKEN",
    "META_IG_USER_ID",
    "CAROUSEL_PUBLIC_BASE_URL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_OWNER_CHAT_ID",
    "TELEGRAM_WEBHOOK_SECRET",
    "GROKBOT_API_KEY_SHA256",
    "CREDENTIALS_ENCRYPTION_KEY",
    "AUTOPILOT_ENABLED",
    "AUTOPILOT_OWNER_USER_ID",
    "AUTOPILOT_DAILY_CAP",
)


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("autopilot_env_parity", CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("checker module spec missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CHECKER_MOD = _load_checker()


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: AE-0359 — fixed interpreter, test-controlled paths
        [PYTHON, str(CHECKER), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def _write_pair(
    tmp_path: Path,
    deploy_values: dict[str, str],
    compose_values: dict[str, str],
) -> tuple[Path, Path]:
    deploy = tmp_path / "deploy.yml"
    compose = tmp_path / "compose.yml"
    deploy.write_text(
        "".join(
            f"            {name}={value}\n" for name, value in deploy_values.items()
        ),
        encoding="utf-8",
    )
    env_body = "".join(
        f"      {name}: {value}\n" for name, value in compose_values.items()
    )
    compose.write_text(
        "services:\n  backend:\n    environment:\n"
        + env_body
        + "  frontend:\n    environment:\n      NEXT_PUBLIC_API_URL: /api\n",
        encoding="utf-8",
    )
    return deploy, compose


def _canonical_values() -> tuple[dict[str, str], dict[str, str]]:
    names = CHECKER_MOD.REQUIRED_ENV_NAMES
    deploy = {name: CHECKER_MOD.sample_deploy_value(name) for name in names}
    compose = {name: CHECKER_MOD.sample_compose_value(name) for name in names}
    return deploy, compose


def test_required_names_match_the_ticket() -> None:
    """AE-0359 lists these variables and no others."""
    assert CHECKER_MOD.REQUIRED_ENV_NAMES == _TICKET_ENV_NAMES


def test_canonical_pair_passes(tmp_path: Path) -> None:
    """A complete pair with the disabled default exits 0."""
    deploy_values, compose_values = _canonical_values()
    deploy, compose = _write_pair(tmp_path, deploy_values, compose_values)

    result = _run(str(deploy), str(compose))

    assert result.returncode == EXIT_OK, result.stderr


def test_repository_files_pass() -> None:
    """The committed prod files satisfy the gate."""
    result = _run()

    assert result.returncode == EXIT_OK, result.stderr
    assert "autopilot env parity OK" in result.stdout


@pytest.mark.parametrize("side", ["deploy", "compose"])
def test_fires_when_one_side_omits_a_variable(tmp_path: Path, side: str) -> None:
    """WHEN the files disagree on an autopilot variable THE gate SHALL fail."""
    deploy_values, compose_values = _canonical_values()
    name = "TELEGRAM_WEBHOOK_SECRET"
    if side == "deploy":
        del deploy_values[name]
    else:
        del compose_values[name]
    deploy, compose = _write_pair(tmp_path, deploy_values, compose_values)

    result = _run(str(deploy), str(compose))

    assert result.returncode == EXIT_VIOLATION, result.stdout + result.stderr
    if side == "deploy":
        assert f"{name} missing from deploy.yml" in result.stderr
        assert f"{name} missing from docker-compose.prod.yml" not in result.stderr
        return
    assert f"{name} missing from docker-compose.prod.yml" in result.stderr
    assert f"{name} missing from deploy.yml" not in result.stderr


def test_comment_does_not_count_as_present(tmp_path: Path) -> None:
    """A commented assignment is still missing."""
    deploy_values, compose_values = _canonical_values()
    name = "GROKBOT_API_KEY_SHA256"
    del deploy_values[name]
    deploy, compose = _write_pair(tmp_path, deploy_values, compose_values)
    deploy.write_text(
        f"            # {name}=not-wired\n" + deploy.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = _run(str(deploy), str(compose))

    assert result.returncode == EXIT_VIOLATION
    assert f"{name} missing from deploy.yml" in result.stderr


def test_frontend_service_does_not_satisfy_backend(tmp_path: Path) -> None:
    """The variable must be on the backend service, not another service."""
    deploy_values, compose_values = _canonical_values()
    name = "META_IG_USER_ID"
    moved = compose_values.pop(name)
    deploy, compose = _write_pair(tmp_path, deploy_values, compose_values)
    compose.write_text(
        compose.read_text(encoding="utf-8") + f"      {name}: {moved}\n",
        encoding="utf-8",
    )

    result = _run(str(deploy), str(compose))

    assert result.returncode == EXIT_VIOLATION
    assert f"{name} missing from docker-compose.prod.yml" in result.stderr


def test_fires_when_autopilot_enabled_defaults_true(tmp_path: Path) -> None:
    """The committed default must stay false on both surfaces."""
    deploy_values, compose_values = _canonical_values()
    deploy_values["AUTOPILOT_ENABLED"] = "true"
    compose_values["AUTOPILOT_ENABLED"] = "${AUTOPILOT_ENABLED:-true}"
    deploy, compose = _write_pair(tmp_path, deploy_values, compose_values)

    result = _run(str(deploy), str(compose))

    assert result.returncode == EXIT_VIOLATION
    assert "AUTOPILOT_ENABLED must default to false in deploy.yml" in result.stderr
    assert "docker-compose.prod.yml backend environment" in result.stderr


def test_literal_false_and_numeric_cap_pass(tmp_path: Path) -> None:
    """Literal false and a numeric cap are valid committed defaults."""
    deploy_values, compose_values = _canonical_values()
    deploy_values["AUTOPILOT_ENABLED"] = "false"
    compose_values["AUTOPILOT_ENABLED"] = "false"
    deploy_values["AUTOPILOT_DAILY_CAP"] = "1"
    compose_values["AUTOPILOT_DAILY_CAP"] = "1"
    deploy, compose = _write_pair(tmp_path, deploy_values, compose_values)

    result = _run(str(deploy), str(compose))

    assert result.returncode == EXIT_OK, result.stderr


def test_fires_when_public_base_url_is_wrong(tmp_path: Path) -> None:
    """Meta must be given the public site origin."""
    deploy_values, compose_values = _canonical_values()
    deploy_values["CAROUSEL_PUBLIC_BASE_URL"] = "https://example.com"
    deploy, compose = _write_pair(tmp_path, deploy_values, compose_values)

    result = _run(str(deploy), str(compose))

    assert result.returncode == EXIT_VIOLATION
    assert (
        "CAROUSEL_PUBLIC_BASE_URL must be https://marinssolutions.com" in result.stderr
    )
    assert "deploy.yml" in result.stderr


def test_fires_when_daily_cap_has_no_default(tmp_path: Path) -> None:
    """An empty cap would crash integer settings parsing."""
    deploy_values, compose_values = _canonical_values()
    deploy_values["AUTOPILOT_DAILY_CAP"] = ""
    compose_values["AUTOPILOT_DAILY_CAP"] = "${AUTOPILOT_DAILY_CAP:-}"
    deploy, compose = _write_pair(tmp_path, deploy_values, compose_values)

    result = _run(str(deploy), str(compose))

    assert result.returncode == EXIT_VIOLATION
    assert (
        "AUTOPILOT_DAILY_CAP must have a numeric default in deploy.yml" in result.stderr
    )
    assert "docker-compose.prod.yml backend environment" in result.stderr


def test_usage_and_unreadable_paths(tmp_path: Path) -> None:
    """One argument is a usage error. A missing file is a violation."""
    usage = _run("only-one")
    assert usage.returncode == EXIT_USAGE

    missing = _run(str(tmp_path / "absent.yml"), str(tmp_path / "also.yml"))
    assert missing.returncode == EXIT_VIOLATION
    assert "unreadable" in missing.stderr
