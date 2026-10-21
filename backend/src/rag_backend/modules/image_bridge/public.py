"""Public facade of the image bridge bounded context.

Cross-module code imports only these symbols (also re-exported from the
package ``__init__``). The HTTP router stays off the facade, as in
autopilot: model registration imports the facade, and pulling the router in
would make infrastructure depend on the API layer.
"""

from rag_backend.modules.image_bridge.bootstrap import (
    build_carousel_openai_service,
    build_grokbot_image_service,
    missing_image_bridge_settings,
    report_image_bridge_config,
)
from rag_backend.modules.image_bridge.domain.exceptions import ImageBridgeConfigError

__all__ = [
    "ImageBridgeConfigError",
    "build_carousel_openai_service",
    "build_grokbot_image_service",
    "missing_image_bridge_settings",
    "register_persistence_models",
    "report_image_bridge_config",
]


def register_persistence_models() -> tuple[str, ...]:
    """Import the ORM model so its table attaches to ``Base.metadata``."""
    from rag_backend.modules.image_bridge.infrastructure.models import (
        ImageBridgeJobModel,
    )

    return (ImageBridgeJobModel.__tablename__,)
