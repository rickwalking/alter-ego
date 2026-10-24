"""Web latency under load, measured the way the idle production baseline was.

Round-robin over the four public routes at a fixed rate, from outside the box,
total request time per request (DNS + connect + TTFB + body), browser
User-Agent. Prints one JSON line: count, errors, p50, p95, p99, max (ms).

Usage:
    python load_p95.py <base url> <seconds> [rate] [--samples FILE]
    python load_p95.py --summarize <baseline samples> <loaded samples>

``--samples`` appends every request (ms, ok) to FILE as JSON lines, so windows
measured separately can be summarised together. ``--summarize`` prints both p95
values and whether the loaded p95 stays within 20 % of the baseline.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
import urllib.error
import urllib.request

ROUTES = ("/", "/api/health", "/blog", "/carousels")
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36"
)
TIMEOUT_SECONDS = 15
PERCENT = 100
P95_BUDGET = 1.2
SAMPLES_FLAG = "--samples"
SUMMARIZE_FLAG = "--summarize"


def fetch(url: str) -> tuple[float, bool]:
    """Milliseconds for one request and whether it answered 200."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            response.read()
            ok = response.status == 200
    except (urllib.error.URLError, TimeoutError):
        ok = False
    return (time.monotonic() - started) * 1000, ok


def percentile(samples: list[float], rank: int) -> float:
    """The ``rank``-th percentile (nearest rank)."""
    ordered = sorted(samples)
    index = max(0, min(len(ordered) - 1, round(rank / PERCENT * len(ordered)) - 1))
    return ordered[index]


def summary(samples: list[float], errors: int) -> dict[str, float | int]:
    """Count, errors and the latency percentiles of ``samples``."""
    return {
        "count": len(samples),
        "errors": errors,
        "p50": round(statistics.median(samples)),
        "p95": round(percentile(samples, 95)),
        "p99": round(percentile(samples, 99)),
        "max": round(max(samples)),
    }


def run(
    base: str, seconds: float, rate: float, sink: str | None = None
) -> dict[str, float | int]:
    """Send requests for ``seconds`` at ``rate`` per second; summarise."""
    samples: list[float] = []
    errors = 0
    interval = 1 / rate
    deadline = time.monotonic() + seconds
    index = 0
    while time.monotonic() < deadline:
        tick = time.monotonic()
        elapsed, ok = fetch(base.rstrip("/") + ROUTES[index % len(ROUTES)])
        index += 1
        samples.append(elapsed)
        errors += 0 if ok else 1
        if sink is not None:
            with open(sink, "a", encoding="utf-8") as handle:
                handle.write(json.dumps({"ms": elapsed, "ok": ok}) + "\n")
        time.sleep(max(0.0, interval - (time.monotonic() - tick)))
    return summary(samples, errors)


def read_samples(path: str) -> tuple[list[float], int]:
    """Latencies and the error count stored by ``--samples``."""
    with open(path, encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    return [float(row["ms"]) for row in rows], sum(1 for row in rows if not row["ok"])


def verdict(baseline_path: str, loaded_path: str) -> dict[str, object]:
    """Both summaries and whether loaded p95 <= 1.2 x baseline p95."""
    baseline = summary(*read_samples(baseline_path))
    loaded = summary(*read_samples(loaded_path))
    return {
        "baseline": baseline,
        "under_generation": loaded,
        "budget_ms": round(baseline["p95"] * P95_BUDGET),
        "within_budget": loaded["p95"] <= baseline["p95"] * P95_BUDGET,
    }


def main(argv: list[str]) -> dict[str, object]:
    """Measure, or summarise two sample files."""
    if argv[0] == SUMMARIZE_FLAG:
        return verdict(argv[1], argv[2])
    sink = argv[argv.index(SAMPLES_FLAG) + 1] if SAMPLES_FLAG in argv else None
    positional = [arg for arg in argv if arg != SAMPLES_FLAG and arg != sink]
    rate = float(positional[2]) if len(positional) > 2 else 2.0
    return dict(run(positional[0], float(positional[1]), rate, sink))


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1:])))
