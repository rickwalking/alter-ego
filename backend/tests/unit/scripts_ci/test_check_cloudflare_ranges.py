"""Rule-fires tests for scripts/ci/check_cloudflare_ranges.py.

The weekly check compares Cloudflare's published ranges with the
``set_real_ip_from`` lines of both nginx configs. A clean pass is not enough:
these tests prove a seeded difference exits 1 and names the ranges, and that a
fetch failure exits 2 instead of passing. No test touches the network.
"""

from __future__ import annotations

import importlib.util
import io
import shutil
import subprocess  # noqa: S404  # integrity-ok: a CLI checker test must invoke a subprocess
import sys
import urllib.error
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CHECKER = REPO_ROOT / "scripts" / "ci" / "check_cloudflare_ranges.py"
PYTHON = shutil.which("python3") or sys.executable

EXIT_OK = 0
EXIT_DIFFERENT = 1
EXIT_UNAVAILABLE = 2

V4 = ["173.245.48.0/20", "103.21.244.0/22"]
V6 = ["2400:cb00::/32", "2606:4700::/32"]
NEW_V4 = "198.51.100.0/24"
OLD_V4 = "103.21.244.0/22"


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("cloudflare_ranges", CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("checker module spec missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CHECKER_MOD = _load_checker()


def _nginx(ranges: list[str]) -> str:
    lines = "\n".join(f"    set_real_ip_from {cidr};" for cidr in ranges)
    return f"http {{\n{lines}\n    real_ip_header CF-Connecting-IP;\n}}\n"


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _published(tmp_path: Path, v4: list[str]) -> list[Path]:
    return [
        _write(tmp_path / "ips-v4", "\n".join(v4) + "\n"),
        _write(tmp_path / "ips-v6", "\n".join(V6) + "\n"),
    ]


def _run(
    published: list[Path], configs: list[Path], summary: Path
) -> subprocess.CompletedProcess[str]:
    args = [PYTHON, str(CHECKER), "--published", *map(str, published)]
    for config in configs:
        args += ["--config", str(config)]
    env = {"PATH": "/usr/bin:/bin", "GITHUB_STEP_SUMMARY": str(summary)}
    return subprocess.run(args, capture_output=True, text=True, check=False, env=env)  # noqa: S603


def _configs(tmp_path: Path, ranges: list[str]) -> list[Path]:
    return [
        _write(tmp_path / "nginx.conf.ssl", _nginx(ranges)),
        _write(tmp_path / "nginx.conf", _nginx(ranges)),
    ]


def test_pass_when_both_configs_match(tmp_path: Path) -> None:
    """Scenario: The pinned ranges match Cloudflare's lists."""
    result = _run(
        _published(tmp_path, V4), _configs(tmp_path, V4 + V6), tmp_path / "summary.md"
    )
    assert result.returncode == EXIT_OK, result.stderr
    assert "4 ranges match in 2 configs" in result.stdout
    assert not (tmp_path / "summary.md").exists()


def test_fires_when_cloudflare_adds_a_range(tmp_path: Path) -> None:
    """Scenario: Cloudflare adds a range."""
    summary = tmp_path / "summary.md"
    result = _run(
        _published(tmp_path, [*V4, NEW_V4]), _configs(tmp_path, V4 + V6), summary
    )
    assert result.returncode == EXIT_DIFFERENT
    assert (
        result.stderr.count(f"added (published by Cloudflare, missing here): {NEW_V4}")
        == 2
    )
    assert NEW_V4 in summary.read_text(encoding="utf-8")


def test_fires_when_cloudflare_retires_a_range(tmp_path: Path) -> None:
    """A range nginx still trusts but Cloudflare no longer publishes is reported as removed."""
    published = [cidr for cidr in V4 if cidr != OLD_V4]
    result = _run(
        _published(tmp_path, published), _configs(tmp_path, V4 + V6), tmp_path / "s.md"
    )
    assert result.returncode == EXIT_DIFFERENT
    assert f"removed (listed here, no longer published): {OLD_V4}" in result.stderr


def test_fires_when_only_one_config_drifts(tmp_path: Path) -> None:
    """Each config is checked on its own; the matching one is not named."""
    ssl, plain = _configs(tmp_path, V4 + V6)
    _write(plain, _nginx(V4[:1] + V6))
    result = _run(_published(tmp_path, V4), [ssl, plain], tmp_path / "s.md")
    assert result.returncode == EXIT_DIFFERENT
    assert f"{plain}: differs" in result.stderr
    assert f"{ssl}: differs" not in result.stderr


def test_config_without_ranges_differs(tmp_path: Path) -> None:
    """A config that lost every set_real_ip_from line is a difference, not a pass."""
    config = _write(tmp_path / "nginx.conf", "http {}\n")
    result = _run(_published(tmp_path, V4), [config], tmp_path / "s.md")
    assert result.returncode == EXIT_DIFFERENT


def test_equivalent_notation_matches(tmp_path: Path) -> None:
    """Ranges are compared as networks, so host bits and case do not count as drift."""
    pinned = ["173.245.48.1/20", "103.21.244.0/22", "2400:CB00::/32", "2606:4700::/32"]
    result = _run(
        _published(tmp_path, V4), _configs(tmp_path, pinned), tmp_path / "s.md"
    )
    assert result.returncode == EXIT_OK, result.stderr


def test_empty_published_list_is_unavailable(tmp_path: Path) -> None:
    """An empty list is a failed fetch, never "ranges match"."""
    files = _published(tmp_path, V4)
    _write(files[0], "\n")
    summary = tmp_path / "s.md"
    result = _run(files, _configs(tmp_path, V4 + V6), summary)
    assert result.returncode == EXIT_UNAVAILABLE
    assert "NOT a pass" in result.stderr
    assert "no ranges found" in summary.read_text(encoding="utf-8")


def test_garbage_published_list_is_unavailable(tmp_path: Path) -> None:
    """An HTML error page served with 200 is not a range list."""
    files = _published(tmp_path, V4)
    _write(files[0], "<html>rate limited</html>\n")
    result = _run(files, _configs(tmp_path, V4 + V6), tmp_path / "s.md")
    assert result.returncode == EXIT_UNAVAILABLE
    assert "not an IP range" in result.stderr


def test_unreadable_config_is_unavailable(tmp_path: Path) -> None:
    """A missing config file is reported as unavailable."""
    result = _run(
        _published(tmp_path, V4), [tmp_path / "missing.conf"], tmp_path / "s.md"
    )
    assert result.returncode == EXIT_UNAVAILABLE
    assert "unreadable" in result.stderr


def test_fetch_failure_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A network error while fetching exits 2 and is never reported as a match."""

    def _refuse(*_args: object, **_kwargs: object) -> object:
        raise urllib.error.URLError("connection refused")

    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(CHECKER_MOD.urllib.request, "urlopen", _refuse)
    assert CHECKER_MOD.main([]) == EXIT_UNAVAILABLE
    err = capsys.readouterr().err
    assert "could not fetch https://www.cloudflare.com/ips-v4" in err
    assert "NOT a pass" in err


def test_fetch_reads_both_lists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --published the check fetches both URLs and compares them."""
    bodies = {CHECKER_MOD.PUBLISHED_URLS[0]: V4, CHECKER_MOD.PUBLISHED_URLS[1]: V6}

    def _serve(request: object, timeout: int) -> io.BytesIO:
        assert timeout == CHECKER_MOD.FETCH_TIMEOUT_SECONDS
        url = request.full_url  # type: ignore[attr-defined]
        return io.BytesIO("\n".join(bodies[url]).encode())

    monkeypatch.setattr(CHECKER_MOD.urllib.request, "urlopen", _serve)
    config = _write(tmp_path / "nginx.conf", _nginx(V4 + V6))
    assert CHECKER_MOD.main(["--config", str(config)]) == EXIT_OK
    assert "4 ranges match in 1 configs" in capsys.readouterr().out


def test_repo_configs_agree_with_each_other() -> None:
    """Both committed nginx configs pin the same ranges (offline sanity check)."""
    ssl, plain = CHECKER_MOD.DEFAULT_CONFIGS
    ssl_ranges = CHECKER_MOD.parse_pinned(ssl.read_text(encoding="utf-8"), str(ssl))
    plain_ranges = CHECKER_MOD.parse_pinned(
        plain.read_text(encoding="utf-8"), str(plain)
    )
    assert ssl_ranges
    assert ssl_ranges == plain_ranges
