"""Unit tests for the provider-agnostic chat-model factory (AE-0285).

Scenarios: see tests/features/llm_provider_toggle.feature
"""

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.chat_model_factory import build_chat_model


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "anthropic_api_key": SecretStr("anthropic-key"),
        "anthropic_model": "claude-sonnet-4-6",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_anthropic_provider_builds_chat_anthropic() -> None:
    # Scenario: Anthropic provider selected
    model = build_chat_model(_settings(llm_provider="anthropic"))
    assert isinstance(model, ChatAnthropic)
    assert model.model == "claude-sonnet-4-6"


def test_glm_provider_with_key_builds_openai_compatible_client() -> None:
    # Scenario: GLM provider selected with a key
    model = build_chat_model(
        _settings(
            llm_provider="glm",
            glm_api_key=SecretStr("glm-key"),
            glm_model="glm-5.2",
            glm_base_url="https://opencode.ai/zen/go/v1",
        )
    )
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "glm-5.2"


def test_glm_provider_without_key_falls_back_to_anthropic() -> None:
    # Scenario: GLM selected but no key (CI / prod not yet configured)
    model = build_chat_model(
        _settings(llm_provider="glm", glm_api_key=SecretStr(""))
    )
    assert isinstance(model, ChatAnthropic)


def test_default_provider_is_glm_but_safe_without_a_key() -> None:
    # The shipped default is "glm"; with no GLM key it must not break — it
    # degrades to Anthropic so CI and an unconfigured prod keep working.
    settings = _settings()
    assert settings.llm_provider == "glm"
    assert isinstance(build_chat_model(settings), ChatAnthropic)
