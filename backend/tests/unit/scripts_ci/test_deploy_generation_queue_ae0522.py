"""Deploy order of the queue one-shot and the worker drain; the worker container.

Scenario: The deploy installs the queue schema and drains the worker
Scenario: The worker container is capped and hardened
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
DEPLOY = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
PROD = REPO_ROOT / "docker-compose.prod.yml"
DEV = REPO_ROOT / "docker-compose.yml"
COMPOSE = "docker compose -f docker-compose.prod.yml"
STEP = "python -m rag_backend.scripts.generation_queue_schema --apply --verify"
ARCHIVED_STEP = "python -m rag_backend.scripts.carousel_archived_at --apply --verify"
DRAIN = f"{COMPOSE} stop -t 300 generation-worker || true"
WORKER = "generation-worker"
WORKER_COMMAND = [
    "pgq",
    "run",
    "rag_backend.worker.main:create_pgqueuer",
    "--heartbeat-timeout",
    "300",
    "--batch-size",
    "1",
]
WEB_ONLY = (
    "TELEGRAM_WEBHOOK_SECRET",
    "GROKBOT_API_KEY_SHA256",
    "CREDENTIALS_ENCRYPTION_KEY",
    "META_IG_ACCESS_TOKEN",
    "ALLOWED_ORIGINS",
)


def _script() -> str:
    return DEPLOY.read_text(encoding="utf-8")


def _index(text: str, needle: str) -> int:
    position = text.find(needle)
    assert position >= 0, f"deploy.yml is missing: {needle}"
    return position


def _service(path: Path, name: str) -> dict[str, object]:
    services = yaml.safe_load(path.read_text(encoding="utf-8"))["services"]
    service = services[name]
    assert isinstance(service, dict)
    return service


def test_queue_step_runs_after_archived_at_and_before_stack_up() -> None:
    """Scenario: The deploy installs the queue schema and drains the worker"""
    text = _script()
    step = _index(text, STEP)
    assert _index(text, "pg_isready") < _index(text, ARCHIVED_STEP) < step
    assert step < _index(text, f"{COMPOSE} up -d\n")
    command = text[text.rfind(COMPOSE, 0, step) : step]
    assert "run --rm --no-deps backend" in command


def test_queue_step_failure_never_keeps_the_stack_down() -> None:
    """Scenario: The deploy installs the queue schema and drains the worker"""
    text = _script()
    step = _index(text, STEP)
    stack_up = _index(text, f"{COMPOSE} up -d\n")
    assert "set +e" in text[text.rfind(COMPOSE, 0, step) - 40 : step]
    between = text[step:stack_up]
    assert "QUEUE_SCHEMA_EXIT=$?" in between
    assert "exit 1" not in between
    final = text.rfind('if [ "$QUEUE_SCHEMA_EXIT" -ne 0 ]')
    assert final > stack_up
    assert "ONE_SHOT_FAILED=1" in text[final : text.find("fi", final)]


def test_worker_drains_before_the_stack_goes_down() -> None:
    """Scenario: The deploy installs the queue schema and drains the worker"""
    text = _script()
    drain = _index(text, DRAIN)
    assert _index(text, f"{COMPOSE} build\n") < drain
    assert drain < _index(text, f"{COMPOSE} down\n")


def test_prod_worker_is_capped_and_hardened() -> None:
    """Scenario: The worker container is capped and hardened"""
    worker = _service(PROD, WORKER)
    backend = _service(PROD, "backend")
    assert worker["build"] == backend["build"]
    assert worker["command"] == WORKER_COMMAND
    assert worker["mem_limit"] == "1344m"
    assert worker["memswap_limit"] == worker["mem_limit"]
    assert worker["cpu_shares"] == 256
    assert worker["cpus"] == 1.0
    assert worker["shm_size"] == "256m"
    assert worker["stop_grace_period"] == "300s"
    assert worker["read_only"] is True
    assert worker["cap_drop"] == ["ALL"]
    assert worker["security_opt"] == ["no-new-privileges:true"]
    assert "ports" not in worker
    assert worker["healthcheck"]["test"] == [
        "CMD",
        "python",
        "-m",
        "rag_backend.worker.healthcheck",
    ]
    assert "carousel_output:/app/output" in worker["volumes"]


def test_prod_worker_gets_no_web_only_secret() -> None:
    """Scenario: The worker container is capped and hardened"""
    environment = _service(PROD, WORKER)["environment"]
    assert isinstance(environment, dict)
    for name in WEB_ONLY:
        assert name not in environment
    assert environment["SECRET_KEY"] == "generation-worker-signs-no-tokens"
    assert environment["CAROUSEL_CHECKPOINT_BACKEND"].startswith(
        "${CAROUSEL_CHECKPOINT_BACKEND"
    )
    backend = _service(PROD, "backend")["environment"]
    assert isinstance(backend, dict)
    assert environment["DATABASE_URL"] == backend["DATABASE_URL"]


def test_dev_stack_runs_the_worker_on_the_postgres_checkpointer() -> None:
    """Scenario: The worker refuses to start without the Postgres checkpointer"""
    worker = _service(DEV, WORKER)
    backend = _service(DEV, "backend")
    assert worker["command"] == WORKER_COMMAND
    for service in (worker, backend):
        environment = service["environment"]
        assert isinstance(environment, dict)
        assert environment["CAROUSEL_CHECKPOINT_BACKEND"] == "postgres"
        assert environment["CAROUSEL_CHECKPOINT_POSTGRES_URL"].startswith(
            "postgresql://"
        )
