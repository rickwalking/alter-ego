"""Rule-fires tests for scripts/ci/check_image_bridge_env_parity.py.

The checker fails the ``backend:autopilot-env`` gate when an image bridge
setting is missing from a prod surface, when a secret is not a GitHub secret
(or a plain setting is), when compose/.env.example turn the flag on by
default, or when deploy.yml drifts from the owner decision (literal flag,
fallback true, the site origin). These tests prove each seeded violation
exits 1.

Gherkin: tests/features/image_bridge.feature
  Scenario: Enabled without the bridge URLs falls back to OpenAI (the settings
  exist on every surface)
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess  # noqa: S404  # integrity-ok: a CLI checker test must invoke a subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CHECKER = REPO_ROOT / "scripts" / "ci" / "check_image_bridge_env_parity.py"
PYTHON = shutil.which("python3") or sys.executable

EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_USAGE = 2

_SECRETS = {"GROKBOT_IMAGE_WEBHOOK_URL", "GROKBOT_IMAGE_WEBHOOK_AUTH_VALUE"}


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("image_bridge_env_parity", CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("checker module spec missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CHECKER_MOD = _load_checker()
NAMES: tuple[str, ...] = CHECKER_MOD.REQUIRED_ENV_NAMES


_DEPLOY_LITERALS = {
    "IMAGE_BRIDGE_ENABLED": "true",
    "IMAGE_BRIDGE_FALLBACK_ENABLED": "true",
    "IMAGE_BRIDGE_PUBLIC_BASE_URL": "https://marinssolutions.com",
}


def _deploy_value(name: str) -> str:
    if name in _SECRETS:
        return "${{ secrets." + name + " }}"
    if name in _DEPLOY_LITERALS:
        return _DEPLOY_LITERALS[name]
    return "${{ vars." + name + " || 'x' }}"


def _compose_value(name: str) -> str:
    if name == "IMAGE_BRIDGE_ENABLED":
        return "${" + name + ":-false}"
    return "${" + name + ":-}"


def _canonical() -> dict[str, dict[str, str]]:
    return {
        "deploy": {name: _deploy_value(name) for name in NAMES},
        "compose": {name: _compose_value(name) for name in NAMES},
        "env": {
            name: "false" if name == "IMAGE_BRIDGE_ENABLED" else "" for name in NAMES
        },
        "settings": {name.lower(): "str" for name in NAMES},
    }


def _write(tmp_path: Path, values: dict[str, dict[str, str]]) -> list[str]:
    deploy = tmp_path / "deploy.yml"
    compose = tmp_path / "compose.yml"
    env = tmp_path / ".env.example"
    settings = tmp_path / "settings.py"
    deploy.write_text(
        "".join(f"            {k}={v}\n" for k, v in values["deploy"].items()),
        encoding="utf-8",
    )
    compose.write_text(
        "services:\n  backend:\n    environment:\n"
        + "".join(f"      {k}: {v}\n" for k, v in values["compose"].items())
        + "  frontend:\n    environment:\n      X: y\n",
        encoding="utf-8",
    )
    env.write_text(
        "".join(f"{k}={v}\n" for k, v in values["env"].items()), encoding="utf-8"
    )
    settings.write_text(
        "class Settings:\n"
        + "".join(f"    {k}: {v} = ''\n" for k, v in values["settings"].items()),
        encoding="utf-8",
    )
    return [str(deploy), str(compose), str(env), str(settings)]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: fixed interpreter, test-controlled paths
        [PYTHON, str(CHECKER), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_required_names_match_the_ticket() -> None:
    assert NAMES == (
        "IMAGE_BRIDGE_ENABLED",
        "IMAGE_BRIDGE_FALLBACK_ENABLED",
        "IMAGE_BRIDGE_TIMEOUT_SECONDS",
        "IMAGE_BRIDGE_MAX_CONCURRENCY",
        "IMAGE_BRIDGE_PUBLIC_BASE_URL",
        "GROKBOT_IMAGE_WEBHOOK_URL",
        "GROKBOT_IMAGE_WEBHOOK_AUTH_HEADER",
        "GROKBOT_IMAGE_WEBHOOK_AUTH_VALUE",
    )


def test_canonical_files_pass(tmp_path: Path) -> None:
    result = _run(*_write(tmp_path, _canonical()))
    assert result.returncode == EXIT_OK, result.stderr


def test_repository_files_pass() -> None:
    result = _run()
    assert result.returncode == EXIT_OK, result.stderr
    assert "image bridge env parity OK" in result.stdout


@pytest.mark.parametrize(
    ("surface", "label"),
    [
        ("deploy", "deploy.yml"),
        ("compose", "docker-compose.prod.yml backend environment"),
        ("env", "backend/.env.example"),
        ("settings", "Settings (settings.py)"),
    ],
)
def test_fires_when_a_surface_omits_a_setting(
    tmp_path: Path, surface: str, label: str
) -> None:
    values = _canonical()
    name = "IMAGE_BRIDGE_TIMEOUT_SECONDS"
    key = name.lower() if surface == "settings" else name
    del values[surface][key]

    result = _run(*_write(tmp_path, values))

    assert result.returncode == EXIT_VIOLATION
    assert f"{name} missing from {label}" in result.stderr


def test_fires_when_the_webhook_url_is_not_a_secret(tmp_path: Path) -> None:
    values = _canonical()
    values["deploy"]["GROKBOT_IMAGE_WEBHOOK_URL"] = "https://hooks.example/x"

    result = _run(*_write(tmp_path, values))

    assert result.returncode == EXIT_VIOLATION
    assert "GROKBOT_IMAGE_WEBHOOK_URL must come from GitHub secrets" in result.stderr


def test_fires_when_a_plain_setting_is_a_secret(tmp_path: Path) -> None:
    values = _canonical()
    values["deploy"]["IMAGE_BRIDGE_MAX_CONCURRENCY"] = (
        "${{ secrets.IMAGE_BRIDGE_MAX_CONCURRENCY }}"
    )

    result = _run(*_write(tmp_path, values))

    assert result.returncode == EXIT_VIOLATION
    assert "IMAGE_BRIDGE_MAX_CONCURRENCY is not a secret" in result.stderr


@pytest.mark.parametrize(
    ("surface", "value", "label"),
    [
        ("compose", "${IMAGE_BRIDGE_ENABLED:-true}", "docker-compose.prod.yml"),
        ("compose", "true", "docker-compose.prod.yml"),
        ("env", "true", "backend/.env.example"),
    ],
)
def test_fires_when_local_surfaces_default_enabled(
    tmp_path: Path, surface: str, value: str, label: str
) -> None:
    values = _canonical()
    values[surface]["IMAGE_BRIDGE_ENABLED"] = value

    result = _run(*_write(tmp_path, values))

    assert result.returncode == EXIT_VIOLATION
    assert "IMAGE_BRIDGE_ENABLED must default to false in " + label in result.stderr


@pytest.mark.parametrize("value", ["true", "false"])
def test_deploy_flag_is_a_reviewed_literal(tmp_path: Path, value: str) -> None:
    """Owner decision: on in prod; flipping the literal off is the rollback."""
    values = _canonical()
    values["deploy"]["IMAGE_BRIDGE_ENABLED"] = value
    result = _run(*_write(tmp_path, values))
    assert result.returncode == EXIT_OK, result.stderr


@pytest.mark.parametrize(
    "value",
    ["${{ vars.IMAGE_BRIDGE_ENABLED || 'true' }}", "yes", ""],
)
def test_fires_when_the_deploy_flag_is_not_a_literal(
    tmp_path: Path, value: str
) -> None:
    values = _canonical()
    values["deploy"]["IMAGE_BRIDGE_ENABLED"] = value
    result = _run(*_write(tmp_path, values))
    assert result.returncode == EXIT_VIOLATION
    assert "IMAGE_BRIDGE_ENABLED must be a literal true or false" in result.stderr


@pytest.mark.parametrize(
    "value", ["false", "${{ vars.IMAGE_BRIDGE_FALLBACK_ENABLED }}"]
)
def test_fires_when_the_deploy_fallback_is_not_true(tmp_path: Path, value: str) -> None:
    values = _canonical()
    values["deploy"]["IMAGE_BRIDGE_FALLBACK_ENABLED"] = value
    result = _run(*_write(tmp_path, values))
    assert result.returncode == EXIT_VIOLATION
    assert "IMAGE_BRIDGE_FALLBACK_ENABLED must be true in deploy.yml" in result.stderr


def test_fires_when_the_deploy_base_url_is_not_the_site(tmp_path: Path) -> None:
    values = _canonical()
    values["deploy"]["IMAGE_BRIDGE_PUBLIC_BASE_URL"] = "https://example.com"
    result = _run(*_write(tmp_path, values))
    assert result.returncode == EXIT_VIOLATION
    assert (
        "IMAGE_BRIDGE_PUBLIC_BASE_URL must be https://marinssolutions.com"
        in result.stderr
    )


def test_fires_when_a_plain_setting_is_a_secret_flag(tmp_path: Path) -> None:
    values = _canonical()
    values["deploy"]["IMAGE_BRIDGE_ENABLED"] = "${{ secrets.IMAGE_BRIDGE_ENABLED }}"
    result = _run(*_write(tmp_path, values))
    assert result.returncode == EXIT_VIOLATION
    assert "IMAGE_BRIDGE_ENABLED is not a secret" in result.stderr


def test_usage_and_unreadable_paths(tmp_path: Path) -> None:
    assert _run("one").returncode == EXIT_USAGE
    missing = _run(*(str(tmp_path / f"absent{i}") for i in range(4)))
    assert missing.returncode == EXIT_VIOLATION
    assert "unreadable" in missing.stderr
