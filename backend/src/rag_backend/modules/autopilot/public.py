"""Public facade for the autopilot bounded context.

Cross-module code imports only the symbols re-exported here (and from the
package ``__init__``). Import Linter rejects imports of the private
subpackages.
"""

from rag_backend.modules.autopilot.api.views import (
    AutopilotRunView,
    InstagramStatusView,
)
from rag_backend.modules.autopilot.application.service import AutopilotService
from rag_backend.modules.autopilot.bootstrap import (
    AutopilotBootstrapDeps,
    AutopilotRunnerTickAdapter,
    AutopilotTickConfig,
    InstagramPublishTickAdapter,
    InstagramTickConfig,
    ManualInstagramPublishRequest,
    TelegramNotifyTickAdapter,
    TelegramTickConfig,
    bootstrap_module,
    build_autopilot_runner_tick,
    build_instagram_publish_tick,
    build_telegram_notify_tick,
    manual_instagram_publish,
    notifier_is_configured,
)
from rag_backend.modules.autopilot.domain.exceptions import InvalidAutopilotTransition
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.publish import ManualPublishOutcome

__all__ = [
    "AutopilotBootstrapDeps",
    "AutopilotRunState",
    "AutopilotRunView",
    "AutopilotRunnerTickAdapter",
    "AutopilotService",
    "AutopilotTickConfig",
    "InstagramPublishTickAdapter",
    "InstagramStatusView",
    "InstagramTickConfig",
    "InvalidAutopilotTransition",
    "ManualInstagramPublishRequest",
    "ManualPublishOutcome",
    "TelegramNotifyTickAdapter",
    "TelegramTickConfig",
    "TransitionCommand",
    "bootstrap_module",
    "build_autopilot_runner_tick",
    "build_instagram_publish_tick",
    "build_telegram_notify_tick",
    "manual_instagram_publish",
    "notifier_is_configured",
    "register_persistence_models",
]


def register_persistence_models() -> tuple[str, ...]:
    """Import ORM models so their tables attach to ``Base.metadata``.

    Returns the registered table names. Callers (the shared model package)
    use the call for its side effect; the tuple keeps the import live.
    """
    from rag_backend.modules.autopilot.infrastructure.models import (
        AutopilotRunModel,
        IntegrationCredentialModel,
        ServedSignalUrlModel,
        TelegramUpdateModel,
        TopicCandidateModel,
    )

    return (
        AutopilotRunModel.__tablename__,
        TopicCandidateModel.__tablename__,
        IntegrationCredentialModel.__tablename__,
        TelegramUpdateModel.__tablename__,
        ServedSignalUrlModel.__tablename__,
    )
