"""Deploy ordering of the blog v1 -> v2 cutover step (AE-0423, ADR-0025).

Feature: backend/tests/features/blog_sections_ae0423.feature
Scenario: The deploy runs the cutover after Postgres and before the app stack
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DEPLOY = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
COMPOSE = "docker compose -f docker-compose.prod.yml"
CUTOVER = "python -m rag_backend.scripts.blog_v1_to_v2 --apply --verify"


def _script() -> str:
    return DEPLOY.read_text(encoding="utf-8")


def _index(text: str, needle: str) -> int:
    position = text.find(needle)
    assert position >= 0, f"deploy.yml is missing: {needle}"
    return position


def test_cutover_runs_between_postgres_health_and_stack_up() -> None:
    text = _script()
    build = _index(text, f"{COMPOSE} build")
    down = _index(text, f"{COMPOSE} down")
    postgres_up = _index(text, f"{COMPOSE} up -d postgres")
    healthy = _index(text, "pg_isready")
    cutover = _index(text, CUTOVER)
    stack_up = _index(text, f"{COMPOSE} up -d\n")

    assert build < down < postgres_up < healthy < cutover < stack_up


def test_cutover_uses_the_freshly_built_image_without_app_overlap() -> None:
    text = _script()
    cutover = _index(text, CUTOVER)
    command_start = text.rfind(COMPOSE, 0, cutover)
    command = text[command_start:cutover]
    assert "run --rm --no-deps backend" in command


def test_cutover_failure_aborts_the_deploy() -> None:
    text = _script()
    cutover = _index(text, CUTOVER)
    script_start = text.rfind("script: |", 0, cutover)
    assert "set -e" in text[script_start:cutover]
    assert "|| true" not in text[cutover : text.find("\n", cutover)]


def test_no_alembic_step_is_coupled_to_the_cutover() -> None:
    text = _script()
    cutover = _index(text, CUTOVER)
    stack_up = _index(text, f"{COMPOSE} up -d\n")
    window = text[text.find(f"{COMPOSE} up -d postgres") : stack_up]
    active = [line for line in window.splitlines() if not line.strip().startswith("#")]
    assert not any("alembic" in line for line in active)
    assert cutover < stack_up
