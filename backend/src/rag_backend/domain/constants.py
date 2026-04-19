"""Domain-level constants."""

# Document statuses
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Valid document statuses
VALID_STATUSES = {STATUS_PENDING, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_FAILED}

# Message roles
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"

# Valid message roles
VALID_ROLES = {ROLE_USER, ROLE_ASSISTANT, ROLE_SYSTEM}
