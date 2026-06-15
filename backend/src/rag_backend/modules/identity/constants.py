"""Module-level constants for the identity bounded context.

Per backend/CLAUDE.md, each context owns its own ``constants`` file and no
magic strings appear in code. These constants identify the module for
tracing/observability and centralize the messages the application layer emits.
"""

# Module identity (used for tracing/observability metadata).
MODULE_NAME = "identity"

# Application-layer error messages (raised as domain errors; inbound adapters
# map them to HTTP responses without changing the existing wire behavior).
ERR_INVALID_CREDENTIALS = "Invalid email or password"
ERR_USER_INACTIVE = "User account is deactivated"
ERR_USER_NOT_FOUND = "User not found"
ERR_CURRENT_CREDENTIAL_INCORRECT = "Current password is incorrect"
ERR_CREDENTIAL_TOO_SHORT = "Password does not meet the minimum length policy"
