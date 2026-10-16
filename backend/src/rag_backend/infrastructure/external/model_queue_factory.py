"""Build a role's model queue from settings (AE-0399).

``LLM_MODEL_QUEUE_<ROLE>`` lists ``<transport>:<model>`` entries in order:
``go:<id>`` is a model on the OpenCode Go API (built by the caller's factory),
``sidecar:<provider>/<id>`` a model served by the OpenCode sidecar. One breaker
registry is shared by every queue in the process, with the log and Telegram
alert listeners attached once.
"""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.language_models import BaseChatModel

from rag_backend.infrastructure.config.llm_queue_constants import (
    QUEUE_ENTRY_SEPARATOR,
    QUEUE_TRANSPORT_SEPARATOR,
    TRANSPORT_GO,
    TRANSPORT_SIDECAR,
)
from rag_backend.infrastructure.config.llm_routing_constants import LLM_ROLE_REASONING
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.model_queue_chat_model import (
    ModelQueueChatModel,
)
from rag_backend.infrastructure.external.opencode_sidecar_model import (
    OpenCodeSidecarChatModel,
)
from rag_backend.infrastructure.llm.model_breaker import BreakerPolicy, BreakerRegistry
from rag_backend.infrastructure.notifications.llm_alerts import (
    TelegramLlmAlerts,
    log_transition,
)

GoModelBuilder = Callable[[str], BaseChatModel]


class _ProcessSingletons:
    """One breaker registry and one alert sender per process, by design."""

    registry: BreakerRegistry | None = None
    alerts: TelegramLlmAlerts | None = None


def queue_spec(settings: Settings, role: str) -> list[tuple[str, str]]:
    """``[(transport, model id), ...]`` for ``role``; empty when unset."""
    raw = (
        settings.llm_model_queue_reasoning
        if role == LLM_ROLE_REASONING
        else settings.llm_model_queue_fast
    )
    entries = [
        item.strip() for item in raw.split(QUEUE_ENTRY_SEPARATOR) if item.strip()
    ]
    return [_parse_entry(entry) for entry in entries]


def _parse_entry(entry: str) -> tuple[str, str]:
    transport, separator, model = entry.partition(QUEUE_TRANSPORT_SEPARATOR)
    if not separator:
        return TRANSPORT_GO, transport
    return transport, model


def build_queue_model(
    settings: Settings, role: str, go_builder: GoModelBuilder
) -> ModelQueueChatModel | None:
    """The role's queue model, or None when no queue is configured."""
    models = [
        _entry_model(settings, entry, go_builder)
        for entry in queue_spec(settings, role)
    ]
    usable = [model for model in models if model is not None]
    if not usable:
        return None
    from rag_backend.infrastructure.external.chat_model_factory import role_timeout

    return ModelQueueChatModel(
        models=usable,
        role=role,
        timeout_seconds=role_timeout(role),
        registry=breaker_registry(settings),
        on_all_down=_alerts(settings).on_all_down,
    )


def _entry_model(
    settings: Settings, entry: tuple[str, str], go_builder: GoModelBuilder
) -> BaseChatModel | None:
    transport, model = entry
    if transport == TRANSPORT_SIDECAR:
        return _sidecar_model(settings, model)
    if transport == TRANSPORT_GO:
        return go_builder(model)
    return None


def _sidecar_model(settings: Settings, model: str) -> BaseChatModel | None:
    if not settings.opencode_sidecar_url:
        return None
    return OpenCodeSidecarChatModel(
        model_name=model,
        base_url=settings.opencode_sidecar_url,
        password=settings.opencode_server_password,
        timeout_seconds=settings.opencode_sidecar_timeout_seconds,
        concurrency=settings.opencode_sidecar_concurrency,
    )


def breaker_registry(settings: Settings) -> BreakerRegistry:
    """The process-wide registry, with the log and alert listeners attached."""
    if _ProcessSingletons.registry is None:
        registry = BreakerRegistry(policy=_policy(settings))
        registry.subscribe(log_transition)
        registry.subscribe(_alerts(settings).on_transition)
        _ProcessSingletons.registry = registry
    return _ProcessSingletons.registry


def _alerts(settings: Settings) -> TelegramLlmAlerts:
    if _ProcessSingletons.alerts is None:
        _ProcessSingletons.alerts = TelegramLlmAlerts(
            token=settings.telegram_alerts_bot_token.get_secret_value(),
            chat_id=settings.telegram_alerts_chat_id,
        )
    return _ProcessSingletons.alerts


def _policy(settings: Settings) -> BreakerPolicy:
    return BreakerPolicy(
        failure_threshold=settings.llm_breaker_failures,
        cooldown=settings.llm_breaker_cooldown_seconds,
        quota_cooldown=settings.llm_breaker_quota_cooldown_seconds,
        fatal_cooldown=settings.llm_breaker_fatal_cooldown_seconds,
    )


__all__ = ["breaker_registry", "build_queue_model", "queue_spec"]
