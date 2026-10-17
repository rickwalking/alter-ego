#!/usr/bin/env python3
"""Autopilot prod env parity (AE-0359).

``deploy.yml`` and the backend service in ``docker-compose.prod.yml`` must
both name every autopilot variable. ``AUTOPILOT_ENABLED`` must default to
false so a deploy does not start the runner. ``CAROUSEL_PUBLIC_BASE_URL``
must be the public site origin. ``AUTOPILOT_DAILY_CAP`` must have a numeric
default so an unset secret does not crash settings parsing.
``AUTOPILOT_DEFAULT_PUBLISH`` (AE-0370) and ``AUTOPILOT_PERSONA_ID`` (AE-0371,
empty default) must be named on both surfaces.
``AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS`` (AE-0407) must be named on both with
a numeric default, like the daily cap (a secret or a GitHub variable).

Usage:
    python3 scripts/ci/check_autopilot_env_parity.py
    python3 scripts/ci/check_autopilot_env_parity.py DEPLOY COMPOSE

Rule-fires regression test (AE-0180):
    backend/tests/unit/scripts_ci/test_check_autopilot_env_parity.py
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DEPLOY = _REPO_ROOT / ".github" / "workflows" / "deploy.yml"
_DEFAULT_COMPOSE = _REPO_ROOT / "docker-compose.prod.yml"

VAR_META_IG_ACCESS_TOKEN = "META_IG_ACCESS_TOKEN"
VAR_META_IG_USER_ID = "META_IG_USER_ID"
VAR_CAROUSEL_PUBLIC_BASE_URL = "CAROUSEL_PUBLIC_BASE_URL"
VAR_TELEGRAM_BOT_TOKEN = "TELEGRAM_BOT_TOKEN"
VAR_TELEGRAM_OWNER_CHAT_ID = "TELEGRAM_OWNER_CHAT_ID"
VAR_TELEGRAM_WEBHOOK_SECRET = "TELEGRAM_WEBHOOK_SECRET"
VAR_GROKBOT_API_KEY_SHA256 = "GROKBOT_API_KEY_SHA256"
VAR_CREDENTIALS_ENCRYPTION_KEY = "CREDENTIALS_ENCRYPTION_KEY"
VAR_AUTOPILOT_ENABLED = "AUTOPILOT_ENABLED"
VAR_AUTOPILOT_OWNER_USER_ID = "AUTOPILOT_OWNER_USER_ID"
VAR_AUTOPILOT_DAILY_CAP = "AUTOPILOT_DAILY_CAP"
# AE-0370: what Telegram Approve does; both surfaces default it to "now".
VAR_AUTOPILOT_DEFAULT_PUBLISH = "AUTOPILOT_DEFAULT_PUBLISH"
# AE-0371 PR #106 review: the autopilot persona; empty = resolve "Pedro" by name.
VAR_AUTOPILOT_PERSONA_ID = "AUTOPILOT_PERSONA_ID"
# AE-0399: the carousel model queue, its OpenCode sidecar and the alerts bot.
VAR_LLM_MODEL_QUEUE_FAST = "LLM_MODEL_QUEUE_FAST"
VAR_LLM_MODEL_QUEUE_REASONING = "LLM_MODEL_QUEUE_REASONING"
VAR_OPENCODE_SIDECAR_URL = "OPENCODE_SIDECAR_URL"
VAR_OPENCODE_SERVER_PASSWORD = "OPENCODE_SERVER_PASSWORD"
VAR_TELEGRAM_ALERTS_BOT_TOKEN = "TELEGRAM_ALERTS_BOT_TOKEN"
VAR_TELEGRAM_ALERTS_CHAT_ID = "TELEGRAM_ALERTS_CHAT_ID"
# AE-0407: reasoning-model attempts of the slide fix; 0 turns them off.
VAR_AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS = "AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS"

REQUIRED_ENV_NAMES: tuple[str, ...] = (
    VAR_META_IG_ACCESS_TOKEN,
    VAR_META_IG_USER_ID,
    VAR_CAROUSEL_PUBLIC_BASE_URL,
    VAR_TELEGRAM_BOT_TOKEN,
    VAR_TELEGRAM_OWNER_CHAT_ID,
    VAR_TELEGRAM_WEBHOOK_SECRET,
    VAR_GROKBOT_API_KEY_SHA256,
    VAR_CREDENTIALS_ENCRYPTION_KEY,
    VAR_AUTOPILOT_ENABLED,
    VAR_AUTOPILOT_OWNER_USER_ID,
    VAR_AUTOPILOT_DAILY_CAP,
    VAR_AUTOPILOT_DEFAULT_PUBLISH,
    VAR_AUTOPILOT_PERSONA_ID,
    VAR_LLM_MODEL_QUEUE_FAST,
    VAR_LLM_MODEL_QUEUE_REASONING,
    VAR_OPENCODE_SIDECAR_URL,
    VAR_OPENCODE_SERVER_PASSWORD,
    VAR_TELEGRAM_ALERTS_BOT_TOKEN,
    VAR_TELEGRAM_ALERTS_CHAT_ID,
    VAR_AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS,
)

PUBLIC_SLIDE_BASE_URL = "https://marinssolutions.com"
DISABLED_VALUE = "false"
DEFAULT_DAILY_CAP = "1"
DEFAULT_PUBLISH_MODE = "now"
DEFAULT_ESCALATION_ATTEMPTS = "2"
DEPLOY_SURFACE = "deploy.yml"
COMPOSE_SURFACE = "docker-compose.prod.yml backend environment"

EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_USAGE = 2

_USAGE = (
    "usage: python3 scripts/ci/check_autopilot_env_parity.py "
    "[deploy.yml docker-compose.prod.yml]"
)

_ASSIGNMENT = re.compile(r"^\s*([A-Z][A-Z0-9_]*)=(.*)$")
_BACKEND_SERVICE = re.compile(r"^  backend:\s*(?:#.*)?$")
_NEXT_SERVICE = re.compile(r"^  [A-Za-z0-9_-]+:\s*(?:#.*)?$")
_ENV_BLOCK = re.compile(r"^( +)environment:\s*(?:#.*)?$")
_ENV_KEY = re.compile(r"^\s+([A-Z][A-Z0-9_]*):\s*(.*)$")
_PUBLIC_URL = re.compile(re.escape(PUBLIC_SLIDE_BASE_URL) + r"(?=[:}'\"\s]|$)")
_COMPOSE_ENABLED = re.compile(
    r"^\$\{" + re.escape(VAR_AUTOPILOT_ENABLED) + r":-" + DISABLED_VALUE + r"\}$"
)
_DEPLOY_ENABLED = re.compile(
    r"^\$\{\{\s*secrets\."
    + re.escape(VAR_AUTOPILOT_ENABLED)
    + r"\s*\|\|\s*['\"]"
    + DISABLED_VALUE
    + r"['\"]\s*\}\}$"
)
_LITERAL_NUMBER = re.compile(r"^[0-9]+$")

MSG_MISSING_DEPLOY = "{name} missing from deploy.yml"
MSG_MISSING_COMPOSE = "{name} missing from docker-compose.prod.yml backend environment"
MSG_ENABLED = VAR_AUTOPILOT_ENABLED + " must default to false in {surface}"
MSG_BASE_URL = (
    VAR_CAROUSEL_PUBLIC_BASE_URL + " must be " + PUBLIC_SLIDE_BASE_URL + " in {surface}"
)
MSG_NUMERIC_DEFAULT = "{name} must have a numeric default in {surface}"
# Variables whose value parses as an int in settings: never empty in prod.
NUMERIC_DEFAULT_NAMES: tuple[str, ...] = (
    VAR_AUTOPILOT_DAILY_CAP,
    VAR_AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS,
)
MSG_UNREADABLE = "unreadable {path}: {reason}"


@dataclass(frozen=True)
class EnvSurfaces:
    """Assignment values from the two prod files."""

    deploy: dict[str, str]
    compose: dict[str, str]


@dataclass(frozen=True)
class SurfacePaths:
    """Files the checker reads."""

    deploy: Path
    compose: Path


@dataclass(frozen=True)
class ReadFailure:
    """A file that could not be read."""

    message: str


@dataclass(frozen=True)
class ValueRule:
    """One value constraint applied to whichever surface defines the name."""

    name: str
    ok: Callable[[str], bool]
    template: str


def sample_deploy_value(name: str) -> str:
    """Canonical deploy.yml value that satisfies the parity rules."""
    if name == VAR_AUTOPILOT_ENABLED:
        return "${{ secrets." + name + " || '" + DISABLED_VALUE + "' }}"
    if name == VAR_AUTOPILOT_DAILY_CAP:
        return "${{ secrets." + name + " || '" + DEFAULT_DAILY_CAP + "' }}"
    if name == VAR_AUTOPILOT_DEFAULT_PUBLISH:
        return "${{ secrets." + name + " || '" + DEFAULT_PUBLISH_MODE + "' }}"
    if name == VAR_CAROUSEL_PUBLIC_BASE_URL:
        return PUBLIC_SLIDE_BASE_URL
    if name == VAR_AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS:
        return "${{ vars." + name + " || '" + DEFAULT_ESCALATION_ATTEMPTS + "' }}"
    return "${{ secrets." + name + " }}"


def sample_compose_value(name: str) -> str:
    """Canonical compose environment value that satisfies the parity rules."""
    if name == VAR_AUTOPILOT_ENABLED:
        return "${" + name + ":-" + DISABLED_VALUE + "}"
    if name == VAR_AUTOPILOT_DAILY_CAP:
        return "${" + name + ":-" + DEFAULT_DAILY_CAP + "}"
    if name == VAR_AUTOPILOT_DEFAULT_PUBLISH:
        return "${" + name + ":-" + DEFAULT_PUBLISH_MODE + "}"
    if name == VAR_CAROUSEL_PUBLIC_BASE_URL:
        return "${" + name + ":-" + PUBLIC_SLIDE_BASE_URL + "}"
    if name == VAR_AUTOPILOT_AUTOFIX_ESCALATION_ATTEMPTS:
        return "${" + name + ":-" + DEFAULT_ESCALATION_ATTEMPTS + "}"
    return "${" + name + ":-}"


def gaps(surfaces: EnvSurfaces) -> list[str]:
    """Return parity failures. Empty means the two files agree."""
    messages: list[str] = []
    for name in REQUIRED_ENV_NAMES:
        messages.extend(_missing(surfaces, name))
    messages.extend(_check_enabled(surfaces))
    messages.extend(_check_base_url(surfaces))
    for name in NUMERIC_DEFAULT_NAMES:
        messages.extend(_check_numeric_default(surfaces, name))
    return messages


def main(argv: list[str]) -> int:
    """Exit 0 when the files agree, 1 on a gap, 2 on usage."""
    paths = _paths(argv)
    if paths is None:
        print(_USAGE, file=sys.stderr)
        return EXIT_USAGE
    loaded = _load(paths)
    if isinstance(loaded, str):
        print(loaded, file=sys.stderr)
        return EXIT_VIOLATION
    found = gaps(loaded)
    if found:
        print("\n".join(found), file=sys.stderr)
        return EXIT_VIOLATION
    print("autopilot env parity OK")
    return EXIT_OK


def _paths(argv: list[str]) -> SurfacePaths | None:
    if not argv:
        return SurfacePaths(deploy=_DEFAULT_DEPLOY, compose=_DEFAULT_COMPOSE)
    if len(argv) == 2:
        return SurfacePaths(deploy=Path(argv[0]), compose=Path(argv[1]))
    return None


def _load(paths: SurfacePaths) -> EnvSurfaces | str:
    deploy_text = _read(paths.deploy)
    if isinstance(deploy_text, ReadFailure):
        return deploy_text.message
    compose_text = _read(paths.compose)
    if isinstance(compose_text, ReadFailure):
        return compose_text.message
    return EnvSurfaces(
        deploy=_deploy_assignments(deploy_text),
        compose=_compose_backend_env(compose_text),
    )


def _read(path: Path) -> str | ReadFailure:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        reason = exc.strerror or "os error"
        return ReadFailure(MSG_UNREADABLE.format(path=path, reason=reason))


def _deploy_assignments(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in text.splitlines():
        match = _ASSIGNMENT.match(line)
        if match is None:
            continue
        found[match.group(1)] = _clean_value(match.group(2))
    return found


def _compose_backend_env(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    in_backend = False
    env_indent = -1
    for line in text.splitlines():
        if not in_backend:
            in_backend = _BACKEND_SERVICE.match(line) is not None
            continue
        if _NEXT_SERVICE.match(line):
            break
        if env_indent < 0:
            opened = _ENV_BLOCK.match(line)
            if opened is not None:
                env_indent = len(opened.group(1))
            continue
        key = _env_key(line, env_indent)
        if key is None:
            if _env_block_ended(line, env_indent):
                env_indent = -1
            continue
        found[key[0]] = key[1]
    return found


def _env_key(line: str, env_indent: int) -> tuple[str, str] | None:
    if not line.strip() or line.lstrip().startswith("#"):
        return None
    indent = len(line) - len(line.lstrip(" "))
    if indent <= env_indent:
        return None
    match = _ENV_KEY.match(line)
    if match is None:
        return None
    return match.group(1), _clean_value(match.group(2))


def _env_block_ended(line: str, env_indent: int) -> bool:
    if not line.strip() or line.lstrip().startswith("#"):
        return False
    indent = len(line) - len(line.lstrip(" "))
    return indent <= env_indent


def _clean_value(value: str) -> str:
    text = value.strip()
    if " #" in text:
        text = text.split(" #", 1)[0].strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    return text


def _missing(surfaces: EnvSurfaces, name: str) -> list[str]:
    messages: list[str] = []
    if name not in surfaces.deploy:
        messages.append(MSG_MISSING_DEPLOY.format(name=name))
    if name not in surfaces.compose:
        messages.append(MSG_MISSING_COMPOSE.format(name=name))
    return messages


def _check_enabled(surfaces: EnvSurfaces) -> list[str]:
    rule = ValueRule(VAR_AUTOPILOT_ENABLED, _enabled_ok, MSG_ENABLED)
    return _when_present(surfaces, rule)


def _check_base_url(surfaces: EnvSurfaces) -> list[str]:
    rule = ValueRule(VAR_CAROUSEL_PUBLIC_BASE_URL, _public_url_ok, MSG_BASE_URL)
    return _when_present(surfaces, rule)


def _check_numeric_default(surfaces: EnvSurfaces, name: str) -> list[str]:
    template = MSG_NUMERIC_DEFAULT.replace("{name}", name)
    rule = ValueRule(name, lambda value: _numeric_default_ok(name, value), template)
    return _when_present(surfaces, rule)


def _when_present(surfaces: EnvSurfaces, rule: ValueRule) -> list[str]:
    messages: list[str] = []
    deploy_value = surfaces.deploy.get(rule.name)
    if deploy_value is not None and not rule.ok(deploy_value):
        messages.append(rule.template.format(surface=DEPLOY_SURFACE))
    compose_value = surfaces.compose.get(rule.name)
    if compose_value is not None and not rule.ok(compose_value):
        messages.append(rule.template.format(surface=COMPOSE_SURFACE))
    return messages


def _enabled_ok(value: str) -> bool:
    if value == DISABLED_VALUE:
        return True
    if _COMPOSE_ENABLED.fullmatch(value):
        return True
    return _DEPLOY_ENABLED.fullmatch(value) is not None


def _public_url_ok(value: str) -> bool:
    return _PUBLIC_URL.search(value) is not None


def _numeric_default_ok(name: str, value: str) -> bool:
    """A literal number, ``${NAME:-N}`` or ``${{ secrets|vars.NAME || 'N' }}``."""
    if _LITERAL_NUMBER.fullmatch(value):
        return True
    compose = re.compile(r"^\$\{" + re.escape(name) + r":-([0-9]+)\}$")
    if compose.fullmatch(value):
        return True
    deploy = re.compile(
        r"^\$\{\{\s*(?:secrets|vars)\."
        + re.escape(name)
        + r"\s*\|\|\s*['\"]([0-9]+)['\"]\s*\}\}$"
    )
    return deploy.fullmatch(value) is not None


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
