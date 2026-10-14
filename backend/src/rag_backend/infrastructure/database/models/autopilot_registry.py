"""Attach autopilot ORM tables to ``Base.metadata`` (AE-0350).

Imported by the models package for that side effect. The import goes through
the autopilot public facade, so this package does not reach module internals.
"""

from rag_backend.modules.autopilot import register_persistence_models

AUTOPILOT_TABLES = register_persistence_models()
