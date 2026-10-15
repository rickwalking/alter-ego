"""Attach the image bridge ORM table to ``Base.metadata`` (AE-0393).

Imported by the models package for that side effect, through the module's
public facade (same pattern as ``autopilot_registry``).
"""

from rag_backend.modules.image_bridge import register_persistence_models

IMAGE_BRIDGE_TABLES = register_persistence_models()
