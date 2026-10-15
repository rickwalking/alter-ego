"""Flagged container wiring and startup validation (AE-0393, AC1/AC2/AC8).

Gherkin: tests/features/image_bridge.feature
  Scenario: Bridge disabled keeps the OpenAI path
  Scenario: Enabled without the bridge URLs falls back to OpenAI
"""

from __future__ import annotations

import pytest
from dependency_injector import providers
from pydantic import SecretStr
from structlog.testing import capture_logs

from rag_backend.bootstrap.startup_validation import run_startup_validations
from rag_backend.domain.constants import IMAGE_MODEL_OPENAI
from rag_backend.domain.constants.carousel import SUPPORTED_IMAGE_COMBOS
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.container import Container
from rag_backend.infrastructure.external.openai_image import OpenAIImageService
from rag_backend.modules.image_bridge import (
    ImageBridgeConfigError,
    build_carousel_openai_service,
    build_grokbot_image_service,
    missing_image_bridge_settings,
    report_image_bridge_config,
)
from rag_backend.modules.image_bridge.application.fallback_image_service import (
    FallbackImageService,
)
from rag_backend.modules.image_bridge.application.grokbot_image_service import (
    GrokBotImageService,
)

_OPENAI_STYLE = next(
    style for model, style in SUPPORTED_IMAGE_COMBOS if model == IMAGE_MODEL_OPENAI
)


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "openai_api_key": SecretStr("sk-test"),
        "carousel_checkpoint_backend": "postgres",
    }
    base.update(overrides)
    return Settings.model_validate(base)


def _enabled(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "image_bridge_enabled": True,
        "grokbot_image_webhook_url": SecretStr("https://hooks.example/x"),
        "image_bridge_public_base_url": "https://marinssolutions.com",
    }
    values.update(overrides)
    return _settings(**values)


def _registry_openai_service(settings: Settings) -> tuple[object, object]:
    container = Container()
    container.settings.override(providers.Object(settings))
    registry = container.image_provider_registry()
    service = registry.resolve(IMAGE_MODEL_OPENAI, _OPENAI_STYLE).service
    return service, container.openai_image_service()


# Scenario: Bridge disabled keeps the OpenAI path
def test_disabled_wires_the_plain_openai_service() -> None:
    service, openai = _registry_openai_service(_settings())
    assert isinstance(openai, OpenAIImageService)
    assert service is openai


def test_default_settings_keep_the_bridge_off() -> None:
    settings = _settings()
    assert settings.image_bridge_enabled is False
    assert settings.image_bridge_fallback_enabled is True
    assert settings.image_bridge_timeout_seconds == 600
    assert settings.image_bridge_max_concurrency == 2
    assert settings.grokbot_image_webhook_auth_header == "Authorization"


# Scenario: Grok Bot returns an image (wired when enabled)
def test_enabled_wires_the_bridge_with_the_openai_fallback() -> None:
    service, openai = _registry_openai_service(_enabled())
    assert isinstance(service, FallbackImageService)
    config = service._config
    assert isinstance(config.primary, GrokBotImageService)
    assert config.fallback is openai
    assert config.fallback_enabled is True


def test_enabled_without_fallback_keeps_the_flag() -> None:
    service = build_carousel_openai_service(
        _enabled(image_bridge_fallback_enabled=False), OpenAIImageService("sk-test")
    )
    assert isinstance(service, FallbackImageService)
    assert service._config.fallback_enabled is False


# Scenario: Enabled without the bridge URLs falls back to OpenAI
@pytest.mark.parametrize(
    ("overrides", "missing"),
    [
        ({"grokbot_image_webhook_url": SecretStr("")}, ["GROKBOT_IMAGE_WEBHOOK_URL"]),
        ({"image_bridge_public_base_url": "  "}, ["IMAGE_BRIDGE_PUBLIC_BASE_URL"]),
        (
            {
                "grokbot_image_webhook_url": SecretStr(""),
                "image_bridge_public_base_url": "",
            },
            ["GROKBOT_IMAGE_WEBHOOK_URL", "IMAGE_BRIDGE_PUBLIC_BASE_URL"],
        ),
    ],
)
def test_misconfigured_bridge_wires_plain_openai(
    overrides: dict[str, object], missing: list[str]
) -> None:
    settings = _enabled(**overrides)
    assert missing_image_bridge_settings(settings) == missing
    service, openai = _registry_openai_service(settings)
    assert service is openai


def test_startup_logs_one_error_naming_only_the_missing_settings() -> None:
    settings = _enabled(
        image_bridge_public_base_url="",
        grokbot_image_webhook_auth_value=SecretStr("Bearer do-not-log"),
    )
    with capture_logs() as logs:
        result = run_startup_validations(settings)
    errors = [log for log in logs if log["log_level"] == "error"]
    assert result is not None
    assert errors == [
        {
            "event": "image_bridge_misconfigured",
            "log_level": "error",
            "missing": ["IMAGE_BRIDGE_PUBLIC_BASE_URL"],
            "image_provider": "openai",
        }
    ]
    assert "hooks.example" not in repr(logs)
    assert "do-not-log" not in repr(logs)


def test_startup_is_silent_when_configured_or_off() -> None:
    for settings in (_enabled(), _settings()):
        with capture_logs() as logs:
            run_startup_validations(settings)
        assert not [log for log in logs if log["event"] == "image_bridge_misconfigured"]
    assert report_image_bridge_config(_enabled()) is True
    assert report_image_bridge_config(_settings()) is False


def test_smoke_builder_works_before_the_flag_is_flipped() -> None:
    disabled_but_configured = _enabled(image_bridge_enabled=False)
    assert isinstance(
        build_grokbot_image_service(disabled_but_configured), GrokBotImageService
    )
    with pytest.raises(ImageBridgeConfigError, match="GROKBOT_IMAGE_WEBHOOK_URL"):
        build_grokbot_image_service(_settings())


def test_callback_dependency_builds_the_use_case() -> None:
    from rag_backend.modules.image_bridge.api.router import get_callback_service
    from rag_backend.modules.image_bridge.application.callback import (
        ImageBridgeCallbackService,
    )

    assert isinstance(get_callback_service(), ImageBridgeCallbackService)
