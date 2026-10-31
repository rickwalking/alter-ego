"""The Meta ads variables reach both prod services; the boost caps stay shipped.

Scenario: Both prod services receive the Meta ads variables with empty defaults
Scenario: No prod surface overrides the shipped boost caps
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from rag_backend.infrastructure.config.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]
DEPLOY = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
PROD = REPO_ROOT / "docker-compose.prod.yml"
SERVICES = ("backend", "generation-worker")
META_ADS = (
    "META_ADS_ACCESS_TOKEN",
    "META_AD_ACCOUNT_ID",
    "META_PAGE_ID",
    "META_ADS_IG_USER_ID",
)
CAP_NAMES = (
    "BOOST_MAX_DAILY_BUDGET_CENTS",
    "BOOST_MIN_DAILY_BUDGET_CENTS",
    "BOOST_MAX_DAYS",
    "BOOST_MAX_TOTAL_CENTS_PER_WEEK",
    "BOOST_MAX_PENDING",
    "BOOST_MAX_MEDIA_AGE_DAYS",
    "BOOST_ALLOWED_COUNTRIES",
    "BOOST_APPROVAL_TTL_HOURS",
    "BOOST_CURRENCY",
    "BOOST_LAUNCH_MAX_ATTEMPTS",
    "BOOST_INSIGHTS_POLL_MINUTES",
)
SAMPLE = {
    "META_ADS_ACCESS_TOKEN": "sample-ads-token",
    "META_AD_ACCOUNT_ID": "1234567890",
    "META_PAGE_ID": "2345678901",
    "META_ADS_IG_USER_ID": "3456789012",
}


def _environment(service: str) -> dict[str, str]:
    services = yaml.safe_load(PROD.read_text(encoding="utf-8"))["services"]
    environment = services[service]["environment"]
    assert isinstance(environment, dict)
    return {str(key): str(value) for key, value in environment.items()}


@pytest.mark.parametrize("service", SERVICES)
def test_service_gets_each_meta_ads_variable_with_an_empty_default(
    service: str,
) -> None:
    """Scenario: Both prod services receive the Meta ads variables with empty defaults"""
    environment = _environment(service)
    for name in META_ADS:
        assert environment.get(name) == "${" + name + ":-}"


def test_deploy_writes_each_meta_ads_variable_from_its_secret() -> None:
    """Scenario: Both prod services receive the Meta ads variables with empty defaults"""
    text = DEPLOY.read_text(encoding="utf-8")
    lines = {line.strip() for line in text.splitlines()}
    for name in META_ADS:
        assert f"{name}=${{{{ secrets.{name} }}}}" in lines


def test_no_prod_surface_overrides_the_shipped_boost_caps() -> None:
    """Scenario: No prod surface overrides the shipped boost caps"""
    surfaces = DEPLOY.read_text(encoding="utf-8") + PROD.read_text(encoding="utf-8")
    for name in CAP_NAMES:
        assert name not in surfaces


def test_settings_read_the_passed_variable_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Both prod services receive the Meta ads variables with empty defaults"""
    for name, value in SAMPLE.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-meta-ads-env!!")
    monkeypatch.setenv("ANON_SECRET_KEY", "test-anon-secret-for-meta-ads-env!")
    settings = Settings()
    assert settings.meta_ads_access_token.get_secret_value() == SAMPLE[META_ADS[0]]
    assert settings.meta_ad_account_id == SAMPLE[META_ADS[1]]
    assert settings.meta_page_id == SAMPLE[META_ADS[2]]
    assert settings.meta_ads_ig_user_id == SAMPLE[META_ADS[3]]
