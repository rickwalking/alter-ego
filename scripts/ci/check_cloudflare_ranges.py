#!/usr/bin/env python3
"""nginx's pinned Cloudflare ranges must match Cloudflare's published lists (AE-0592).

nginx trusts ``CF-Connecting-IP`` only from the ``set_real_ip_from`` ranges in
``nginx/nginx.conf.ssl`` and ``nginx/nginx.conf`` (AE-0589). Those ranges are a
pinned copy of <https://www.cloudflare.com/ips-v4> and ``/ips-v6``. This check
fetches both lists and compares them with each config, so a weekly CI job
notices when Cloudflare publishes or retires a range.

Exit codes:
    0  every config lists exactly the published ranges
    1  a config differs (added and removed ranges are printed, and written to
       ``$GITHUB_STEP_SUMMARY`` when set)
    2  a list could not be fetched or parsed, or a config could not be read;
       never reported as "ranges match"

Usage:
    python3 scripts/ci/check_cloudflare_ranges.py
    python3 scripts/ci/check_cloudflare_ranges.py --published FILE [FILE ...]
        [--config FILE ...]

``--published`` reads local copies instead of fetching (used by the tests, which
never touch the network).

Rule-fires regression test (AE-0180):
    backend/tests/unit/scripts_ci/test_check_cloudflare_ranges.py
"""

from __future__ import annotations

import argparse
import http.client
import ipaddress
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIGS = (
    _REPO_ROOT / "nginx" / "nginx.conf.ssl",
    _REPO_ROOT / "nginx" / "nginx.conf",
)
PUBLISHED_HOST = "www.cloudflare.com"
PUBLISHED_PATHS = ("/ips-v4", "/ips-v6")
HTTP_GET = "GET"
HTTP_OK = 200
FETCH_TIMEOUT_SECONDS = 30
USER_AGENT = "alter-ego-cloudflare-ranges-check"
ENV_STEP_SUMMARY = "GITHUB_STEP_SUMMARY"
ENCODING = "utf-8"

EXIT_OK = 0
EXIT_DIFFERENT = 1
EXIT_UNAVAILABLE = 2

_REAL_IP_FROM = re.compile(
    r"^\s*set_real_ip_from\s+(?P<cidr>[^;\s]+)\s*;", re.MULTILINE
)

MSG_OK = "Cloudflare ranges OK: {count} ranges match in {configs} configs"
MSG_DIFF = "{path}: differs from Cloudflare's published ranges"
MSG_ADDED = "  added (published by Cloudflare, missing here): {cidr}"
MSG_REMOVED = "  removed (listed here, no longer published): {cidr}"
MSG_FETCH_FAILED = "could not fetch https://{host}{path}: {reason}"
MSG_HTTP_STATUS = "HTTP {status}"
MSG_EMPTY = "{source}: no ranges found"
MSG_BAD_RANGE = "{source}: not an IP range: {value!r}"
MSG_UNREADABLE = "{source}: unreadable ({reason})"
MSG_UNAVAILABLE = "Cloudflare ranges check could not run; this is NOT a pass."
SUMMARY_TITLE = "## Cloudflare ranges in nginx"
SUMMARY_FIX = (
    "Update the `set_real_ip_from` lines in both nginx configs "
    "(docs/deployment/DEPLOYMENT_GUIDE.md, Client Addresses and Rate Limits)."
)

Network = ipaddress.IPv4Network | ipaddress.IPv6Network


class RangesUnavailableError(Exception):
    """A published list or a config could not be read or parsed."""


@dataclass(frozen=True)
class ConfigDiff:
    """Ranges one config is missing (added) and lists in excess (removed)."""

    path: str
    added: tuple[str, ...]
    removed: tuple[str, ...]

    @property
    def differs(self) -> bool:
        """True when the config does not list exactly the published ranges."""
        return bool(self.added or self.removed)


def parse_network(value: str, source: str) -> Network:
    """One CIDR (or bare address) as a normalised network."""
    try:
        return ipaddress.ip_network(value.strip(), strict=False)
    except ValueError as exc:
        raise RangesUnavailableError(
            MSG_BAD_RANGE.format(source=source, value=value)
        ) from exc


def parse_published(text: str, source: str) -> set[Network]:
    """The ranges in one published list (one CIDR per line)."""
    values = [line.strip() for line in text.splitlines() if line.strip()]
    if not values:
        raise RangesUnavailableError(MSG_EMPTY.format(source=source))
    return {parse_network(value, source) for value in values}


def parse_pinned(text: str, source: str) -> set[Network]:
    """The ``set_real_ip_from`` ranges in one nginx config."""
    return {
        parse_network(match.group("cidr"), source)
        for match in _REAL_IP_FROM.finditer(text)
    }


def compare(published: set[Network], pinned: set[Network], path: str) -> ConfigDiff:
    """What one config must add and remove to match the published ranges."""
    return ConfigDiff(
        path=path,
        added=_sorted_text(published - pinned),
        removed=_sorted_text(pinned - published),
    )


def fetch(path: str) -> str:
    """One published list over HTTPS; a network error or non-200 is unavailable."""
    connection = http.client.HTTPSConnection(
        PUBLISHED_HOST, timeout=FETCH_TIMEOUT_SECONDS
    )
    try:
        connection.request(HTTP_GET, path, headers={"User-Agent": USER_AGENT})
        response = connection.getresponse()
        status, body = response.status, response.read()
    except (OSError, http.client.HTTPException) as exc:
        raise _fetch_error(path, str(exc)) from exc
    finally:
        connection.close()
    if status != HTTP_OK:
        raise _fetch_error(path, MSG_HTTP_STATUS.format(status=status))
    return body.decode(ENCODING, errors="replace")


def read_file(path: Path) -> str:
    """A local file's text; an unreadable file is unavailable."""
    try:
        return path.read_text(encoding=ENCODING)
    except OSError as exc:
        reason = exc.strerror or "os error"
        raise RangesUnavailableError(
            MSG_UNREADABLE.format(source=path, reason=reason)
        ) from exc


def load_published(local: list[Path] | None) -> set[Network]:
    """The published ranges, from local copies when given, else fetched."""
    if local:
        return set().union(
            *(parse_published(read_file(path), str(path)) for path in local)
        )
    return set().union(
        *(
            parse_published(fetch(path), PUBLISHED_HOST + path)
            for path in PUBLISHED_PATHS
        )
    )


def diff_configs(published: set[Network], configs: list[Path]) -> list[ConfigDiff]:
    """One diff per nginx config."""
    return [
        compare(published, parse_pinned(read_file(path), str(path)), str(path))
        for path in configs
    ]


def report_lines(diffs: list[ConfigDiff]) -> list[str]:
    """Plain-text lines naming each differing config's added and removed ranges."""
    lines: list[str] = []
    for diff in (item for item in diffs if item.differs):
        lines.append(MSG_DIFF.format(path=diff.path))
        lines.extend(MSG_ADDED.format(cidr=cidr) for cidr in diff.added)
        lines.extend(MSG_REMOVED.format(cidr=cidr) for cidr in diff.removed)
    return lines


def write_summary(lines: list[str]) -> None:
    """Append the report to the GitHub step summary when running in Actions."""
    target = os.environ.get(ENV_STEP_SUMMARY)
    if not target:
        return
    body = "\n".join([SUMMARY_TITLE, "", "```", *lines, "```", "", SUMMARY_FIX, ""])
    with Path(target).open("a", encoding=ENCODING) as handle:
        handle.write(body)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Command-line options."""
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None
    )
    parser.add_argument(
        "--published", nargs="+", type=Path, help="local copies of the published lists"
    )
    parser.add_argument(
        "--config",
        action="append",
        type=Path,
        help="nginx config to check (repeatable)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Exit 0 on a match, 1 on a difference, 2 when the check cannot run."""
    args = parse_args(argv)
    configs: list[Path] = args.config or list(DEFAULT_CONFIGS)
    try:
        published = load_published(args.published)
        diffs = diff_configs(published, configs)
    except RangesUnavailableError as exc:
        lines = [str(exc), MSG_UNAVAILABLE]
        print("\n".join(lines), file=sys.stderr)
        write_summary(lines)
        return EXIT_UNAVAILABLE
    lines = report_lines(diffs)
    if lines:
        print("\n".join(lines), file=sys.stderr)
        write_summary(lines)
        return EXIT_DIFFERENT
    print(MSG_OK.format(count=len(published), configs=len(configs)))
    return EXIT_OK


def _fetch_error(path: str, reason: str) -> RangesUnavailableError:
    return RangesUnavailableError(
        MSG_FETCH_FAILED.format(host=PUBLISHED_HOST, path=path, reason=reason)
    )


def _sorted_text(networks: set[Network]) -> tuple[str, ...]:
    return tuple(str(network) for network in sorted(networks, key=_sort_key))


def _sort_key(network: Network) -> tuple[int, int, int]:
    return (network.version, int(network.network_address), network.prefixlen)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
