"""Autopilot bounded context (AE-0350).

Cross-module consumers import from this package only::

    from rag_backend.modules.autopilot import AutopilotService, TransitionCommand
"""

from rag_backend.modules.autopilot.public import (
    AutopilotBootstrapDeps,
    AutopilotRunnerTickAdapter,
    AutopilotRunState,
    AutopilotRunView,
    AutopilotService,
    AutopilotTickConfig,
    InstagramPublishTickAdapter,
    InstagramStatusView,
    InstagramTickConfig,
    InvalidAutopilotTransition,
    ManualInstagramPublishRequest,
    ManualPublishOutcome,
    TransitionCommand,
    bootstrap_module,
    build_autopilot_runner_tick,
    build_instagram_publish_tick,
    manual_instagram_publish,
    register_persistence_models,
)

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
    "TransitionCommand",
    "bootstrap_module",
    "build_autopilot_runner_tick",
    "build_instagram_publish_tick",
    "manual_instagram_publish",
    "register_persistence_models",
]
