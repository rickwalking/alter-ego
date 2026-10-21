"""Image bridge bounded context (ADR-0022).

Generates carousel images through the owner's Grok Bot (async webhook +
OpenAI-compatible callback), with OpenAI as the fallback. Cross-module
consumers import from this package only::

    from rag_backend.modules.image_bridge import build_carousel_openai_service
"""

from rag_backend.modules.image_bridge.public import (
    ImageBridgeConfigError,
    build_carousel_openai_service,
    build_grokbot_image_service,
    missing_image_bridge_settings,
    register_persistence_models,
    report_image_bridge_config,
)

__all__ = [
    "ImageBridgeConfigError",
    "build_carousel_openai_service",
    "build_grokbot_image_service",
    "missing_image_bridge_settings",
    "register_persistence_models",
    "report_image_bridge_config",
]
