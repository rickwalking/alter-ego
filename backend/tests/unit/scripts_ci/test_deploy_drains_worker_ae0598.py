"""Shape of the deploy drain in deploy.yml and the OpenCode init in compose.

Each check is a function that lists what is wrong, so it is proven on the real
files AND on a seeded violation (the deploy.yml / compose shape from before the
change), in the rule-fires style. Feature file:
tests/features/deploy_drains_worker_ae0598.feature
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
DEPLOY = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
PROD = REPO_ROOT / "docker-compose.prod.yml"
COMPOSE = "docker compose -f docker-compose.prod.yml"
DRAIN_SCRIPT = "bash scripts/deploy/drain-generation-worker.sh"
DRAIN_BOUND_SECONDS = 240
STOP_GRACE_SECONDS = 60
OLD_STOP_GRACE_SECONDS = 300
DRAIN = f"{DRAIN_SCRIPT} drain docker-compose.prod.yml {DRAIN_BOUND_SECONDS} 5\n"
STOP = f"{COMPOSE} stop -t {STOP_GRACE_SECONDS} generation-worker || true\n"
CLEAR = f"{DRAIN_SCRIPT} clear docker-compose.prod.yml\n"
BUILD = f"{COMPOSE} build\n"
DOWN = f"{COMPOSE} down -t 120 --remove-orphans\n"
UP = f"{COMPOSE} up -d\n"
DRIFT = "python -m rag_backend.infrastructure.database.check_drift_cli"
SSH_STEP = "Deploy to DigitalOcean via SSH"
COMMAND_TIMEOUT = "15m"
KEPT_CHECKS = (
    "python -m rag_backend.scripts.blog_v1_to_v2 --apply --verify",
    "python -m rag_backend.scripts.palette_timestamptz --apply --verify",
    "python -m rag_backend.scripts.carousel_phase_index --apply --verify",
    "python -m rag_backend.scripts.content_versions_index --apply --verify",
    "python -m rag_backend.scripts.carousel_archived_at --apply --verify",
    "python -m rag_backend.scripts.generation_queue_schema --apply --verify",
    "python -m rag_backend.scripts.ig_insight_columns --apply --verify",
    "python -m rag_backend.scripts.must_change_password_column --apply --verify",
    "python -m rag_backend.scripts.token_version_column --apply --verify",
    DRIFT,
    "--- Container status ---",
    "--- Redis auth probe (AE-0302) ---",
    "bash scripts/deploy/check-env-permissions.sh",
    'if [ "$ONE_SHOT_FAILED" -ne 0 ]; then',
)

POST_START_RETRIES = (
    "python -m rag_backend.scripts.must_change_password_column --apply --verify",
    "python -m rag_backend.scripts.token_version_column --apply --verify",
)


def _in_order(text: str, needles: tuple[str, ...]) -> bool:
    positions = [text.find(needle) for needle in needles]
    return -1 not in positions and positions == sorted(positions)


def deploy_problems(text: str) -> list[str]:
    """What is wrong with the drain in a deploy.yml text; empty when it is right."""
    problems: list[str] = []
    if not _in_order(text, (BUILD, DRAIN, STOP, DOWN)):
        problems.append("drain must run after the build, before the stop and down")
    if text.count("stop -t") != 1:
        problems.append("exactly one worker stop")
    if not _in_order(text, (UP, CLEAR, DRIFT)):
        problems.append("the clear must run after up -d and before the drift check")
    problems.extend(
        f"missing check: {check}" for check in KEPT_CHECKS if check not in text
    )
    problems.extend(
        f"missing post-start retry: {retry}"
        for retry in POST_START_RETRIES
        if text.count(retry) < 2
    )
    return problems


def ssh_timeout(text: str) -> object:
    """The command_timeout of the deploy ssh step."""
    steps = yaml.safe_load(text)["jobs"]["deploy"]["steps"]
    step = next(step for step in steps if step.get("name") == SSH_STEP)
    return step["with"].get("command_timeout")


def opencode_problems(compose: dict[str, object]) -> list[str]:
    """What keeps opencode from stopping on SIGTERM; empty when it is right."""
    services = compose["services"]
    assert isinstance(services, dict)
    opencode = services["opencode"]
    assert isinstance(opencode, dict)
    if opencode.get("init") is not True:
        return ["opencode runs as PID 1 without an init"]
    return []


def _seeded_old_deploy() -> str:
    old_stop = f"{COMPOSE} stop -t {OLD_STOP_GRACE_SECONDS} generation-worker || true\n"
    text = DEPLOY.read_text(encoding="utf-8")
    text = text.replace(" " * 12 + DRAIN, "").replace(" " * 12 + CLEAR, "")
    return text.replace(STOP, old_stop)


def test_the_deploy_drains_before_it_stops_the_worker() -> None:
    """Scenario: The deploy drains, stops with a short grace and keeps every check"""
    assert deploy_problems(DEPLOY.read_text(encoding="utf-8")) == []


def test_the_drain_check_fires_on_the_old_deploy() -> None:
    """Scenario: The deploy drains, stops with a short grace and keeps every check"""
    problems = deploy_problems(_seeded_old_deploy())
    assert "drain must run after the build, before the stop and down" in problems
    assert "the clear must run after up -d and before the drift check" in problems


def test_the_drain_check_fires_when_a_check_is_dropped() -> None:
    """Scenario: The deploy drains, stops with a short grace and keeps every check"""
    text = DEPLOY.read_text(encoding="utf-8").replace(DRIFT, "true")
    assert f"missing check: {DRIFT}" in deploy_problems(text)


def test_the_drain_check_fires_when_a_post_start_retry_is_dropped() -> None:
    """Scenario: The deploy drains, stops with a short grace and keeps every check"""
    text = DEPLOY.read_text(encoding="utf-8")
    retry = POST_START_RETRIES[1]
    first = text.find(retry) + len(retry)
    seeded = text[:first] + text[first:].replace(retry, "true")
    assert f"missing post-start retry: {retry}" in deploy_problems(seeded)


def test_the_phase_wait_stays_at_the_old_300_seconds() -> None:
    """Scenario: The deploy drains, stops with a short grace and keeps every check"""
    assert DRAIN_BOUND_SECONDS + STOP_GRACE_SECONDS == OLD_STOP_GRACE_SECONDS


def test_the_ssh_command_timeout_is_15_minutes() -> None:
    """Scenario: The deploy drains, stops with a short grace and keeps every check"""
    text = DEPLOY.read_text(encoding="utf-8")
    assert ssh_timeout(text) == COMMAND_TIMEOUT
    seeded = text.replace(f"{' ' * 10}command_timeout: {COMMAND_TIMEOUT}\n", "")
    assert ssh_timeout(seeded) is None


def test_opencode_runs_under_an_init() -> None:
    """Scenario: The OpenCode sidecar stops on SIGTERM"""
    compose = yaml.safe_load(PROD.read_text(encoding="utf-8"))
    assert opencode_problems(compose) == []
    compose["services"]["opencode"].pop("init")
    assert opencode_problems(compose) == ["opencode runs as PID 1 without an init"]
