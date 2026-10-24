"""Fail when the validation environment holds a production credential.

The droplet's ``.env`` is built from stubs (``env_template.sh``). This check
compares the SHA-256 of every value in it with the SHA-256 of every production
value (``prod-hashes.txt``, one hex digest per line, produced read-only from the
production ``.env`` and never containing a value). Any match exits 1 and names
the variable, never the value. Empty values and values shorter than 8
characters are not compared (ports, booleans, ``1``).

Usage: ``python credential_check.py <droplet .env> <prod hash file>``.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

EXIT_CLEAN = 0
EXIT_LEAK = 1
EXIT_USAGE = 2
MIN_SECRET_CHARS = 8


def env_values(text: str) -> dict[str, str]:
    """``NAME=value`` pairs of an env file (quotes stripped, blank lines skipped)."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        name, sep, value = line.partition("=")
        if not sep or not name.strip() or name.lstrip().startswith("#"):
            continue
        values[name.strip()] = value.strip().strip("'\"")
    return values


def digest(value: str) -> str:
    """Hex SHA-256 of a value."""
    return hashlib.sha256(value.encode()).hexdigest()


def leaks(env_text: str, prod_hashes: set[str]) -> list[str]:
    """Names of the variables whose value is a production value."""
    return sorted(
        name
        for name, value in env_values(env_text).items()
        if len(value) >= MIN_SECRET_CHARS and digest(value) in prod_hashes
    )


def main(argv: list[str]) -> int:
    """Check one env file against one hash list."""
    if len(argv) != 2:
        print("usage: credential_check.py <env file> <prod hash file>", file=sys.stderr)
        return EXIT_USAGE
    env_text = Path(argv[0]).read_text(encoding="utf-8")
    prod_hashes = {
        line.strip().lower()
        for line in Path(argv[1]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    if not prod_hashes:
        print("credential check: empty production hash list", file=sys.stderr)
        return EXIT_USAGE
    found = leaks(env_text, prod_hashes)
    if found:
        print(f"credential check: PRODUCTION VALUE in {', '.join(found)}", file=sys.stderr)
        return EXIT_LEAK
    print(f"credential check: clean ({len(prod_hashes)} production hashes compared)")
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
