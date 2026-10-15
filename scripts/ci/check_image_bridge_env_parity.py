#!/usr/bin/env python3
"""Image bridge prod env parity (AE-0393).

Every image bridge setting must be named in ``deploy.yml``, the backend
service of ``docker-compose.prod.yml`` and ``backend/.env.example``, and
declared on ``Settings``. The webhook URL and auth value must come from
GitHub secrets in ``deploy.yml``; the other settings must not.

Owner decision (2026-10-15): prod runs the bridge with the OpenAI fallback.
So in ``deploy.yml`` ``IMAGE_BRIDGE_ENABLED`` is a literal ``true``/``false``
(the switch and the rollback live in reviewed code), the fallback is a
literal ``true`` and the public base URL is the site origin. Compose and
``.env.example`` keep the flag defaulting to false.

Runs inside the ``backend:autopilot-env`` gate, after the autopilot checker,
and reuses its file parsers.

Usage:
    python3 scripts/ci/check_image_bridge_env_parity.py
    python3 scripts/ci/check_image_bridge_env_parity.py \
        DEPLOY COMPOSE ENV_EXAMPLE SETTINGS

Rule-fires regression test (AE-0180):
    backend/tests/unit/scripts_ci/test_check_image_bridge_env_parity.py
"""

from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HERE = Path(__file__).resolve().parent
_DEFAULTS = (
    _REPO_ROOT / ".github" / "workflows" / "deploy.yml",
    _REPO_ROOT / "docker-compose.prod.yml",
    _REPO_ROOT / "backend" / ".env.example",
    _REPO_ROOT
    / "backend"
    / "src"
    / "rag_backend"
    / "infrastructure"
    / "config"
    / "settings.py",
)

VAR_ENABLED = "IMAGE_BRIDGE_ENABLED"
VAR_FALLBACK = "IMAGE_BRIDGE_FALLBACK_ENABLED"
VAR_PUBLIC_BASE_URL = "IMAGE_BRIDGE_PUBLIC_BASE_URL"
PUBLIC_BASE_URL = "https://marinssolutions.com"
DEPLOY_ENABLED_VALUES = frozenset({"true", "false"})
DEPLOY_FALLBACK_VALUE = "true"
VAR_WEBHOOK_URL = "GROKBOT_IMAGE_WEBHOOK_URL"
VAR_AUTH_VALUE = "GROKBOT_IMAGE_WEBHOOK_AUTH_VALUE"
SECRET_ENV_NAMES: tuple[str, ...] = (VAR_WEBHOOK_URL, VAR_AUTH_VALUE)
REQUIRED_ENV_NAMES: tuple[str, ...] = (
    VAR_ENABLED,
    VAR_FALLBACK,
    "IMAGE_BRIDGE_TIMEOUT_SECONDS",
    "IMAGE_BRIDGE_MAX_CONCURRENCY",
    VAR_PUBLIC_BASE_URL,
    VAR_WEBHOOK_URL,
    "GROKBOT_IMAGE_WEBHOOK_AUTH_HEADER",
    VAR_AUTH_VALUE,
)

EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_USAGE = 2
_ARG_COUNT = 4

_SECRET_REF = re.compile(r"\$\{\{\s*secrets\.")
_ENABLED_FALSE = re.compile(r"^(?:false|\$\{" + VAR_ENABLED + r":-false\})$")
_SETTINGS_FIELD = re.compile(r"^\s{4}([a-z][a-z0-9_]*)\s*:", re.MULTILINE)

MSG_MISSING = "{name} missing from {surface}"
MSG_NEEDS_GH_VAULT = "{name} must come from GitHub secrets in deploy.yml"
MSG_PLAIN_IN_GH_VAULT = (
    "{name} is not a secret; use a plain value or vars in deploy.yml"
)
MSG_ENABLED = VAR_ENABLED + " must default to false in {surface}"
MSG_DEPLOY_ENABLED = VAR_ENABLED + " must be a literal true or false in deploy.yml"
MSG_DEPLOY_FALLBACK = VAR_FALLBACK + " must be true in deploy.yml (OpenAI fallback)"
MSG_DEPLOY_BASE_URL = (
    VAR_PUBLIC_BASE_URL + " must be " + PUBLIC_BASE_URL + " in deploy.yml"
)
MSG_UNREADABLE = "unreadable {path}: {reason}"
SURFACE_DEPLOY = "deploy.yml"
SURFACE_COMPOSE = "docker-compose.prod.yml backend environment"
SURFACE_ENV_EXAMPLE = "backend/.env.example"
SURFACE_SETTINGS = "Settings (settings.py)"
_USAGE = (
    "usage: python3 scripts/ci/check_image_bridge_env_parity.py "
    "[deploy.yml docker-compose.prod.yml .env.example settings.py]"
)


@dataclass(frozen=True)
class BridgeSurfaces:
    """Assignments per surface, plus the declared Settings fields."""

    deploy: dict[str, str]
    compose: dict[str, str]
    env_example: dict[str, str]
    settings_fields: frozenset[str]


def _autopilot_checker() -> ModuleType:
    path = _HERE / "check_autopilot_env_parity.py"
    spec = importlib.util.spec_from_file_location("_autopilot_env_parity", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(MSG_UNREADABLE.format(path=path, reason="no spec"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_PARSERS = _autopilot_checker()


def gaps(surfaces: BridgeSurfaces) -> list[str]:
    """Return parity failures. Empty means every surface agrees."""
    messages: list[str] = []
    for name in REQUIRED_ENV_NAMES:
        messages.extend(_missing(surfaces, name))
    messages.extend(_secret_rules(surfaces.deploy))
    messages.extend(_enabled_rules(surfaces))
    messages.extend(_deploy_value_rules(surfaces.deploy))
    return messages


def parse_surfaces(texts: tuple[str, str, str, str]) -> BridgeSurfaces:
    """Parse the four files' text."""
    deploy, compose, env_example, settings = texts
    return BridgeSurfaces(
        deploy=_PARSERS._deploy_assignments(deploy),
        compose=_PARSERS._compose_backend_env(compose),
        env_example=_PARSERS._deploy_assignments(env_example),
        settings_fields=frozenset(_SETTINGS_FIELD.findall(settings)),
    )


def main(argv: list[str]) -> int:
    """Exit 0 when every surface agrees, 1 on a gap, 2 on usage."""
    if argv and len(argv) != _ARG_COUNT:
        print(_USAGE, file=sys.stderr)
        return EXIT_USAGE
    paths = tuple(Path(arg) for arg in argv) if argv else _DEFAULTS
    texts: list[str] = []
    for path in paths:
        try:
            texts.append(path.read_text(encoding="utf-8"))
        except OSError as exc:
            reason = exc.strerror or "os error"
            print(MSG_UNREADABLE.format(path=path, reason=reason), file=sys.stderr)
            return EXIT_VIOLATION
    found = gaps(parse_surfaces((texts[0], texts[1], texts[2], texts[3])))
    if found:
        print("\n".join(found), file=sys.stderr)
        return EXIT_VIOLATION
    print("image bridge env parity OK")
    return EXIT_OK


def _missing(surfaces: BridgeSurfaces, name: str) -> list[str]:
    present = (
        (SURFACE_DEPLOY, name in surfaces.deploy),
        (SURFACE_COMPOSE, name in surfaces.compose),
        (SURFACE_ENV_EXAMPLE, name in surfaces.env_example),
        (SURFACE_SETTINGS, name.lower() in surfaces.settings_fields),
    )
    return [
        MSG_MISSING.format(name=name, surface=surface)
        for surface, ok in present
        if not ok
    ]


def _secret_rules(deploy: dict[str, str]) -> list[str]:
    messages: list[str] = []
    for name in REQUIRED_ENV_NAMES:
        value = deploy.get(name)
        if value is None:
            continue
        is_secret = _SECRET_REF.search(value) is not None
        if name in SECRET_ENV_NAMES and not is_secret:
            messages.append(MSG_NEEDS_GH_VAULT.format(name=name))
        if name not in SECRET_ENV_NAMES and is_secret:
            messages.append(MSG_PLAIN_IN_GH_VAULT.format(name=name))
    return messages


def _enabled_rules(surfaces: BridgeSurfaces) -> list[str]:
    messages: list[str] = []
    for surface, values in (
        (SURFACE_COMPOSE, surfaces.compose),
        (SURFACE_ENV_EXAMPLE, surfaces.env_example),
    ):
        value = values.get(VAR_ENABLED)
        if value is not None and _ENABLED_FALSE.fullmatch(value) is None:
            messages.append(MSG_ENABLED.format(surface=surface))
    return messages


def _deploy_value_rules(deploy: dict[str, str]) -> list[str]:
    checks = (
        (VAR_ENABLED, lambda value: value in DEPLOY_ENABLED_VALUES, MSG_DEPLOY_ENABLED),
        (
            VAR_FALLBACK,
            lambda value: value == DEPLOY_FALLBACK_VALUE,
            MSG_DEPLOY_FALLBACK,
        ),
        (
            VAR_PUBLIC_BASE_URL,
            lambda value: value == PUBLIC_BASE_URL,
            MSG_DEPLOY_BASE_URL,
        ),
    )
    return [
        message
        for name, ok, message in checks
        if name in deploy and not ok(deploy[name])
    ]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
