"""Validate the generation queue on the production droplet with one QA carousel.

Run from the developer laptop, only when Pedro says go (``validate.sh --target
prod``). It never touches a real autopilot run, never publishes and never prints
a secret:

1. Refuses to start between 11:05 and 13:30 UTC, while a deploy workflow runs,
   when the site is not healthy, when any other generation run is active or a QA
   project already exists.
2. Measures an idle p95 of four public pages (2 req/s), then keeps the same gentle
   load running for the whole run.
3. Starts exactly one ``[QA <date>] queue validation`` carousel as the owner
   through the dashboard API (``prod_qa_run.py`` inside the backend container)
   and approves each gate up to the final review, which it never approves.
4. Chaos, each once and only while no other generation run is active: ``docker
   kill`` of the generation worker during the first worker phase, then
   ``docker compose restart generation-worker`` during a later one.
5. Every 15 s: ``docker stats``, each container's ``OOMKilled``, host
   ``free -m`` and the site health. Aborts on two non-200 health checks in a
   row, a rolling p95 over 3x the baseline, any ``OOMKilled`` or less than
   300 MiB available.
6. Always (also on abort or Ctrl-C): verifies duplicates and attempts, deletes
   the QA carousel and its rows, and writes the report.

Usage: ``python prod_validate.py`` (``PROD_HOST``, ``PROD_BASE_URL`` and
``VALIDATION_RESULTS`` override the defaults).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime, time as day_time
from pathlib import Path
from types import ModuleType

HERE = Path(__file__).resolve().parent
HOST = os.environ.get("PROD_HOST", "root@206.189.180.85")
BASE_URL = os.environ.get("PROD_BASE_URL", "https://marinssolutions.com")
RESULTS = Path(os.environ.get("VALIDATION_RESULTS", str(Path.home() / "queue-validation-results")))
APP_DIR = "/opt/alter-ego"
COMPOSE = f"cd {APP_DIR} && docker compose -f docker-compose.prod.yml"
WORKER = "generation-worker"
REPO = "rickwalking/alter-ego"
DEPLOY_WORKFLOW = "deploy.yml"
QUIET_START = day_time(11, 5)
QUIET_END = day_time(13, 30)
LOAD_RATE = 2.0
BASELINE_SECONDS = 180
TICK_SECONDS = 15
RUN_TIMEOUT_SECONDS = 2 * 3600
ROLLING_SAMPLES = 120
P95_ABORT_FACTOR = 3.0
HEALTH_FAILURES_ABORT = 2
AVAILABLE_ABORT_MIB = 300
HTTP_OK = 200
RUNNING = "running"
KEY, STATUS = 0, 1


@dataclass
class Tick:
    """What one 15 s sample saw."""

    health_failures: int
    rolling_p95: float
    available_mib: int
    oom_killed: list[str] = field(default_factory=list)


def refuse_reason(now: datetime, *, deploy_running: bool) -> str | None:
    """Why the run must not start now, or None."""
    clock = now.astimezone(UTC).time()
    if QUIET_START <= clock < QUIET_END:
        return "refusing: 11:05-13:30 UTC is the autopilot batch window"
    if deploy_running:
        return "refusing: a deploy workflow is running"
    return None


def preflight_reason(preflight: dict[str, object]) -> str | None:
    """Why the queue is not quiet enough for the QA run, or None."""
    if int(str(preflight.get("other_active_runs", 0))) > 0:
        return "refusing: another generation run is active"
    if preflight.get("qa_projects"):
        return "refusing: a QA project already exists; clean it up first"
    return None


def abort_reason(tick: Tick, baseline_p95: float) -> str | None:
    """Why the run must stop now, or None."""
    if tick.health_failures >= HEALTH_FAILURES_ABORT:
        return f"abort: health non-200 {tick.health_failures} times in a row"
    if tick.oom_killed:
        return f"abort: OOMKilled {', '.join(tick.oom_killed)}"
    if tick.available_mib < AVAILABLE_ABORT_MIB:
        return f"abort: only {tick.available_mib} MiB available"
    if baseline_p95 > 0 and tick.rolling_p95 > baseline_p95 * P95_ABORT_FACTOR:
        return f"abort: p95 {tick.rolling_p95:.0f} ms > {P95_ABORT_FACTOR}x baseline {baseline_p95:.0f} ms"
    return None


def chaos_due(
    runs: list[list[object]], other_active: int, done: dict[str, str]
) -> tuple[str, str] | None:
    """``(step, run key)`` to take now, or None.

    Only while a worker job of the QA run is running and no other generation run
    is active: the kill hits the first running job, the restart a later one.
    """
    if other_active > 0:
        return None
    running = [str(run[KEY]) for run in runs if run[STATUS] == RUNNING]
    if not running:
        return None
    if "kill" not in done:
        return "kill", running[0]
    if "restart" not in done and running[0] != done["kill"]:
        return "restart", running[0]
    return None


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ssh(command: str, stdin: Path | None = None) -> str:
    """Run one command on the droplet; its stdout."""
    handle = stdin.open("rb") if stdin is not None else None
    try:
        result = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", HOST, command],
            stdin=handle,
            capture_output=True,
            check=True,
            timeout=1800,
        )
    finally:
        if handle is not None:
            handle.close()
    return result.stdout.decode()


def _driver_command(*args: str) -> list[str]:
    return ["ssh", "-o", "BatchMode=yes", HOST, f"{COMPOSE} exec -T backend python - {' '.join(args)}"]


def _merged(lines: list[str]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for line in lines:
        if line.startswith("{"):
            payload.update(json.loads(line))
    return payload


def driver(*args: str) -> dict[str, object]:
    """One ``prod_qa_run.py`` command inside the backend container; its JSON lines merged."""
    with (HERE / "prod_qa_run.py").open("rb") as script:
        result = subprocess.run(
            _driver_command(*args), stdin=script, capture_output=True, check=False, timeout=1800
        )
    payload = _merged(result.stdout.decode().splitlines())
    if result.returncode != 0:
        payload["driver_exit"] = result.returncode
    return payload


def start_in_background(date: str) -> tuple[subprocess.Popen[str], str]:
    """Start the QA carousel; return once it exists (its first phases keep running)."""
    script = (HERE / "prod_qa_run.py").open("rb")
    process = subprocess.Popen(
        _driver_command("start", date), stdin=script, stdout=subprocess.PIPE, text=True
    )
    assert process.stdout is not None
    for line in process.stdout:
        project = _merged([line]).get("project_id")
        if project:
            return process, str(project)
    return process, ""


def deploy_running() -> bool:
    """A deploy workflow run is queued or in progress."""
    for status in ("in_progress", "queued"):
        found = subprocess.run(
            ["gh", "run", "list", "--repo", REPO, "--workflow", DEPLOY_WORKFLOW, "--status", status,
             "--json", "databaseId", "-q", "length"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if found not in ("", "0"):
            return True
    return False


def healthy() -> bool:
    """The public health route answers 200."""
    try:
        with urllib.request.urlopen(BASE_URL + "/api/health", timeout=15) as response:
            return response.status == HTTP_OK
    except (urllib.error.URLError, TimeoutError):
        return False


def sample(out: Path) -> tuple[int, list[str]]:
    """Append docker stats, OOMKilled and free -m to the samples; available MiB and OOM names."""
    stamp = int(time.time())
    text = ssh(
        "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}';"
        " echo '--oom'; docker inspect --format '{{.Name}}\t{{.State.OOMKilled}}\t{{.RestartCount}}' $(docker ps -aq);"
        " echo '--free'; free -m | awk '/Mem:/{print $3\"\\t\"$7}'"
    )
    with out.open("a", encoding="utf-8") as handle:
        handle.writelines(f"{stamp}\t{line}\n" for line in text.splitlines())
    oom_part = text.split("--oom\n", 1)[1].split("--free\n", 1)[0]
    oom = [line.split("\t")[0].lstrip("/") for line in oom_part.splitlines() if "\ttrue\t" in line]
    available = int(text.split("--free\n", 1)[1].split("\t")[1])
    return available, oom


def rolling_p95(samples: Path, load: ModuleType) -> float:
    """p95 of the latest requests of the running load."""
    if not samples.exists():
        return 0.0
    latencies, _errors = load.read_samples(str(samples))
    window = latencies[-ROLLING_SAMPLES:]
    return float(load.percentile(window, 95)) if window else 0.0


def chaos(step_name: str) -> None:
    """Kill the worker (the restart policy brings it back) or restart it gracefully."""
    if step_name == "kill":
        ssh(f"docker kill --signal KILL $({COMPOSE} ps -q {WORKER}); sleep 20; {COMPOSE} up -d {WORKER}")
        return
    ssh(f"{COMPOSE} restart {WORKER}")


def drive(run_dir: Path, load: ModuleType, baseline_p95: float, project: str) -> dict[str, object]:
    """Approve gates, take the chaos steps, watch the box; the outcome."""
    done: dict[str, str] = {}
    failures = 0
    deadline = time.monotonic() + RUN_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        failures = 0 if healthy() else failures + 1
        available, oom = sample(run_dir / "memory-samples.tsv")
        tick = Tick(failures, rolling_p95(run_dir / "load-run.jsonl", load), available, oom)
        reason = abort_reason(tick, baseline_p95)
        if reason is not None:
            return {"outcome": reason, "chaos": done}
        state = driver("step", project)
        with (run_dir / "steps.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(state) + "\n")
        if state.get("done"):
            return {"outcome": "reached final review", "chaos": done}
        runs = state.get("runs") or []
        assert isinstance(runs, list)
        due = chaos_due(runs, int(str(state.get("other_active_runs", 0))), done)
        if due is not None:
            chaos(due[0])
            done[due[0]] = due[1]
        time.sleep(TICK_SECONDS)
    return {"outcome": "timeout", "chaos": done}


def main() -> int:
    """Guards, baseline, the run, the cleanup and the report."""
    reason = refuse_reason(datetime.now(UTC), deploy_running=deploy_running())
    if reason is None and not healthy():
        reason = "refusing: the site is not healthy"
    preflight = driver("preflight") if reason is None else {}
    reason = reason or preflight_reason(preflight)
    if reason is not None:
        print(reason)
        return 1
    load = _load("load_p95")
    run_dir = RESULTS / f"prod-{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
    run_dir.mkdir(parents=True)
    load.run(BASE_URL, BASELINE_SECONDS, LOAD_RATE, str(run_dir / "load-baseline.jsonl"))
    baseline_p95 = rolling_p95(run_dir / "load-baseline.jsonl", load)
    loader = subprocess.Popen(
        [sys.executable, str(HERE / "load_p95.py"), BASE_URL, str(RUN_TIMEOUT_SECONDS), str(LOAD_RATE),
         "--samples", str(run_dir / "load-run.jsonl")],
        stdout=subprocess.DEVNULL,
    )
    project = ""
    starter: subprocess.Popen[str] | None = None
    report: dict[str, object] = {"baseline_p95_ms": baseline_p95}
    try:
        starter, project = start_in_background(f"{datetime.now(UTC):%Y-%m-%d}")
        report["project_id"] = project
        if project:
            report.update(drive(run_dir, load, baseline_p95, project))
        else:
            report["outcome"] = "the QA carousel was not created"
    except KeyboardInterrupt:
        report["outcome"] = "interrupted"
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        report["outcome"] = f"error: {type(exc).__name__}"
    finally:
        loader.terminate()
        if starter is not None and starter.poll() is None:
            starter.terminate()
        projects = [project] if project else [str(p) for p in driver("preflight").get("qa_projects") or []]
        for qa_project in projects:
            report["verify"] = driver("verify", qa_project)
            report["cleanup"] = driver("cleanup", qa_project)
        if (run_dir / "load-run.jsonl").exists():
            report["p95"] = load.verdict(str(run_dir / "load-baseline.jsonl"), str(run_dir / "load-run.jsonl"))
        (run_dir / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(json.dumps(report, default=str))
    return 0 if report.get("outcome") == "reached final review" else 1


if __name__ == "__main__":
    sys.exit(main())
