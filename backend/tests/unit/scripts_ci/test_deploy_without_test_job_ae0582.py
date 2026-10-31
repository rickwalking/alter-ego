"""The deploy workflow only deploys; tests stay in PR CI."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
DEPLOY = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
ON_KEY = True


def _workflow() -> dict[object, object]:
    loaded = yaml.safe_load(DEPLOY.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _deploy_job() -> dict[str, object]:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["deploy"]
    assert isinstance(job, dict)
    return job


def test_the_only_job_is_deploy_and_it_waits_on_nothing() -> None:
    """Scenario: The deploy workflow has no test job and the deploy waits on nothing"""
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    assert list(jobs) == ["deploy"]
    assert "needs" not in _deploy_job()


def test_deploy_keeps_its_guard_concurrency_and_manual_trigger() -> None:
    """Scenario: The deploy keeps its main-only guard, serial concurrency and manual trigger"""
    workflow = _workflow()
    assert _deploy_job()["if"] == "github.ref == 'refs/heads/main'"
    assert workflow["concurrency"] == {
        "group": "prod-deploy",
        "cancel-in-progress": False,
    }
    triggers = workflow[ON_KEY]
    assert isinstance(triggers, dict)
    assert triggers["push"] == {"branches": ["main"]}
    assert "workflow_dispatch" in triggers
