"""Public facade for the autopilot bounded context.

Cross-module code imports only the symbols re-exported here (and from the
package ``__init__``). Import Linter rejects imports of the private
subpackages.
"""

from rag_backend.modules.autopilot.api.views import AutopilotRunView
from rag_backend.modules.autopilot.application.service import AutopilotService
from rag_backend.modules.autopilot.bootstrap import (
    AutopilotBootstrapDeps,
    bootstrap_module,
)
from rag_backend.modules.autopilot.domain.exceptions import InvalidAutopilotTransition
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRunState,
    TransitionCommand,
)

__all__ = [
    "AutopilotBootstrapDeps",
    "AutopilotRunState",
    "AutopilotRunView",
    "AutopilotService",
    "InvalidAutopilotTransition",
    "TransitionCommand",
    "bootstrap_module",
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
        TelegramUpdateModel,
        TopicCandidateModel,
    )

    return (
        AutopilotRunModel.__tablename__,
        TopicCandidateModel.__tablename__,
        IntegrationCredentialModel.__tablename__,
        TelegramUpdateModel.__tablename__,
    )
