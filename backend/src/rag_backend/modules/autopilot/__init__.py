"""Autopilot bounded context (AE-0350).

Cross-module consumers import from this package only::

    from rag_backend.modules.autopilot import AutopilotService, TransitionCommand
"""

from rag_backend.modules.autopilot.public import (
    AutopilotBootstrapDeps,
    AutopilotRunState,
    AutopilotRunView,
    AutopilotService,
    InvalidAutopilotTransition,
    TransitionCommand,
    bootstrap_module,
    register_persistence_models,
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
