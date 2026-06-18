"""Constants for application configuration and deployment environments.

Lives in the infrastructure/config layer because deployment-environment
semantics (which environments are "production-like" vs. dev/test) are a
composition-root concern, not a domain concept.
"""

from __future__ import annotations

# Deployment environment identifiers (value of ``Settings.environment``).
ENVIRONMENT_DEVELOPMENT = "development"
ENVIRONMENT_TEST = "test"
ENVIRONMENT_STAGING = "staging"
ENVIRONMENT_PRODUCTION = "production"

# Environments where the app may run with non-durable/ephemeral configuration
# without tripping startup hardening guards (memory checkpointer, missing
# image-provider keys are tolerated here).
NON_PRODUCTION_ENVIRONMENTS: frozenset[str] = frozenset({
    ENVIRONMENT_DEVELOPMENT,
    ENVIRONMENT_TEST,
})
