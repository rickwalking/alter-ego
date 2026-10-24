"""Attach the generation queue ORM table to ``Base.metadata``.

Imported by the models package for that side effect, through the module's
public facade (same pattern as ``image_bridge_registry``).
"""

from rag_backend.modules.generation_queue import register_persistence_models

GENERATION_QUEUE_TABLES = register_persistence_models()
