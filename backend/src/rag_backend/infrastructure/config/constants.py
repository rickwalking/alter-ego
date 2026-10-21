"""Constants for application configuration and deployment environments.

Lives in the infrastructure/config layer because deployment-environment
semantics (which environments are "production-like" vs. dev/test) are a
composition-root concern, not a domain concept.

``NON_PRODUCTION_ENVIRONMENTS`` may run with non-durable configuration without
tripping the startup hardening guards (a memory checkpointer and missing
image-provider keys are tolerated there).
"""

from __future__ import annotations

ENVIRONMENT_DEVELOPMENT = "development"
ENVIRONMENT_TEST = "test"
ENVIRONMENT_STAGING = "staging"
ENVIRONMENT_PRODUCTION = "production"

NON_PRODUCTION_ENVIRONMENTS: frozenset[str] = frozenset({
    ENVIRONMENT_DEVELOPMENT,
    ENVIRONMENT_TEST,
})
