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
from rag_backend.modules.autopilot.bootstrap_credentials import (
    CredentialRefreshTickAdapter,
    CredentialTickConfig,
    build_credential_refresh_tick,
    build_stored_instagram_token_provider,
    credential_tick_config,
    encryption_key_usable,
    prepare_instagram_credentials,
)
from rag_backend.modules.autopilot.domain.exceptions import (
    InvalidAutopilotTransition,
    ManualPublishRefusedError,
)
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
    "CredentialRefreshTickAdapter",
    "CredentialTickConfig",
    "InstagramPublishTickAdapter",
    "InstagramStatusView",
    "InstagramTickConfig",
    "InvalidAutopilotTransition",
    "ManualInstagramPublishRequest",
    "ManualPublishOutcome",
    "ManualPublishRefusedError",
    "TelegramNotifyTickAdapter",
    "TelegramTickConfig",
    "TransitionCommand",
    "bootstrap_module",
    "build_autopilot_runner_tick",
    "build_credential_refresh_tick",
    "build_instagram_publish_tick",
    "build_stored_instagram_token_provider",
    "build_telegram_notify_tick",
    "credential_tick_config",
    "encryption_key_usable",
    "manual_instagram_publish",
    "notifier_is_configured",
    "prepare_instagram_credentials",
    "register_persistence_models",
]


def register_persistence_models() -> tuple[str, ...]:
    """Import ORM models so their tables attach to ``Base.metadata``.

    Returns the registered table names. Callers (the shared model package)
    use the call for its side effect; the tuple keeps the import live.
    """
    from rag_backend.modules.autopilot.infrastructure.insights_models import (
        InstagramPostInsightsModel,
    )
    from rag_backend.modules.autopilot.infrastructure.models import (
        AutopilotRunModel,
        InstagramStoryModel,
        IntegrationCredentialModel,
        ManualPublishModel,
        NotifyCursorModel,
        ServedSignalUrlModel,
        TelegramUpdateModel,
        TopicCandidateModel,
        XBrowserSignalModel,
    )

    return (
        AutopilotRunModel.__tablename__,
        TopicCandidateModel.__tablename__,
        IntegrationCredentialModel.__tablename__,
        TelegramUpdateModel.__tablename__,
        ServedSignalUrlModel.__tablename__,
        XBrowserSignalModel.__tablename__,
        ManualPublishModel.__tablename__,
        NotifyCursorModel.__tablename__,
        InstagramStoryModel.__tablename__,
        InstagramPostInsightsModel.__tablename__,
    )
