#!/usr/bin/env python3
"""Container healthchecks must not target ``localhost`` (AE-0390).

busybox ``wget`` in the alpine frontend image resolved ``localhost`` to
``[::1]`` first, while Next.js listens on IPv4 only. The probe was refused
1,201 times in a row and prod ``frontend`` stayed ``unhealthy`` while the site
served 200. A healthcheck must name ``127.0.0.1`` (or a service host) instead.

Scans every compose ``healthcheck:`` block and every Dockerfile
``HEALTHCHECK`` instruction (continuation lines joined).

Usage:
    python3 scripts/ci/check_healthcheck_loopback.py
    python3 scripts/ci/check_healthcheck_loopback.py FILE [FILE ...]

Rule-fires regression test (AE-0180):
    backend/tests/unit/scripts_ci/test_check_healthcheck_loopback.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPOSE_GLOB = "docker-compose*.yml"
_DOCKERFILE_GLOBS = ("Dockerfile*", "*/Dockerfile*")

EXIT_OK = 0
EXIT_VIOLATION = 1

_LOCALHOST = re.compile(r"\blocalhost\b", re.IGNORECASE)
_COMPOSE_HEALTHCHECK = re.compile(r"^(\s*)healthcheck:\s*(?:#.*)?$")
_DOCKER_HEALTHCHECK = re.compile(r"^\s*HEALTHCHECK\b", re.IGNORECASE)
_CONTINUATION = "\\"
_COMMENT = "#"

MSG_VIOLATION = (
    "{path}:{line}: healthcheck targets localhost; use 127.0.0.1 "
    "(localhost may resolve to [::1] while the server listens on IPv4)"
)
MSG_UNREADABLE = "{path}: unreadable ({reason})"
MSG_OK = "healthcheck loopback OK ({count} files)"


@dataclass(frozen=True)
class Finding:
    """One healthcheck line that names localhost."""

    path: Path
    line: int


def default_files(root: Path) -> list[Path]:
    """Compose files and Dockerfiles the gate scans by default."""
    files = sorted(root.glob(_COMPOSE_GLOB))
    for pattern in _DOCKERFILE_GLOBS:
        files.extend(sorted(root.glob(pattern)))
    return [path for path in files if path.is_file()]


def is_compose(path: Path) -> bool:
    """True for a compose YAML file (anything else is read as a Dockerfile)."""
    return path.suffix in {".yml", ".yaml"}


def compose_findings(path: Path, text: str) -> list[Finding]:
    """Lines inside a compose ``healthcheck:`` block that name localhost."""
    findings: list[Finding] = []
    block_indent = -1
    for number, line in enumerate(text.splitlines(), start=1):
        opened = _COMPOSE_HEALTHCHECK.match(line)
        if opened is not None:
            block_indent = len(opened.group(1))
            continue
        if block_indent < 0 or not line.strip():
            continue
        if _indent(line) <= block_indent:
            block_indent = -1
            continue
        if _names_localhost(line):
            findings.append(Finding(path=path, line=number))
    return findings


def dockerfile_findings(path: Path, text: str) -> list[Finding]:
    """``HEALTHCHECK`` instructions (with continuations) that name localhost."""
    findings: list[Finding] = []
    in_healthcheck = False
    for number, line in enumerate(text.splitlines(), start=1):
        if not in_healthcheck:
            in_healthcheck = _DOCKER_HEALTHCHECK.match(line) is not None
        if in_healthcheck and _names_localhost(line):
            findings.append(Finding(path=path, line=number))
        if in_healthcheck and not line.rstrip().endswith(_CONTINUATION):
            in_healthcheck = False
    return findings


def scan(path: Path, text: str) -> list[Finding]:
    """Findings for one file, by kind."""
    if is_compose(path):
        return compose_findings(path, text)
    return dockerfile_findings(path, text)


def main(argv: list[str]) -> int:
    """Exit 0 when no healthcheck names localhost, 1 otherwise."""
    files = [Path(arg) for arg in argv] if argv else default_files(_REPO_ROOT)
    messages: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            reason = exc.strerror or "os error"
            messages.append(MSG_UNREADABLE.format(path=path, reason=reason))
            continue
        messages.extend(
            MSG_VIOLATION.format(path=found.path, line=found.line)
            for found in scan(path, text)
        )
    if messages:
        print("\n".join(messages), file=sys.stderr)
        return EXIT_VIOLATION
    print(MSG_OK.format(count=len(files)))
    return EXIT_OK


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _names_localhost(line: str) -> bool:
    code = line.split(f" {_COMMENT}", 1)[0]
    if code.lstrip().startswith(_COMMENT):
        return False
    return _LOCALHOST.search(code) is not None


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
