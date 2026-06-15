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

# Admin-handler domain errors (inbound adapters map these to the legacy HTTP
# status codes/messages; the strings here are stable contract identifiers, the
# wire message is still formatted at the route to stay byte-identical).
ERR_USER_ALREADY_EXISTS = "User already exists"
ERR_INVALID_ROLE = "Invalid role"
ERR_LAST_ADMIN = "Cannot modify the last admin"
ERR_SELF_DELETE = "Cannot delete your own account"

# Cryptographically secure temp-credential generation policy (mirrors the legacy
# admin route generator exactly so created/reset credentials keep the same shape).
GENERATED_CREDENTIAL_LENGTH = 16
GENERATED_SPECIAL_CHARS = "!@#$%^&*"
