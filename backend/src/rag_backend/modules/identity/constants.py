"""Module-level constants for the identity bounded context.

Per backend/CLAUDE.md, each context owns its own ``constants`` file and no
magic strings appear in code. These constants identify the module for
tracing/observability and centralize the messages the application layer emits.

Inbound adapters map the application error messages to HTTP responses without changing
the wire behavior. The admin-handler error strings are stable contract identifiers; the
wire message is still formatted at the route to stay byte-identical. The temp-credential
policy mirrors the legacy admin route generator, so created and reset credentials keep
the same shape.
"""

MODULE_NAME = "identity"

ERR_INVALID_CREDENTIALS = "Invalid email or password"
ERR_USER_INACTIVE = "User account is deactivated"
ERR_USER_NOT_FOUND = "User not found"
ERR_CURRENT_CREDENTIAL_INCORRECT = "Current password is incorrect"
ERR_CREDENTIAL_UNCHANGED = "New password must differ from the current one"
ERR_CREDENTIAL_TOO_SHORT = "Password does not meet the minimum length policy"

ERR_USER_ALREADY_EXISTS = "User already exists"
ERR_INVALID_ROLE = "Invalid role"
ERR_LAST_ADMIN = "Cannot modify the last admin"
ERR_LAST_ACTIVE_ADMIN_DEACTIVATION = "Cannot deactivate the last active admin"
ERR_SELF_DELETE = "Cannot delete your own account"

GENERATED_CREDENTIAL_LENGTH = 16
GENERATED_SPECIAL_CHARS = "!@#$%^&*"
