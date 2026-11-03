"""Safe failure-cause codes for a failed carousel workflow run.

The cause stored on the carousel row and the generation run is
``<ErrorClass>: <code>``: never the raw exception message, a prompt or user
content.
"""

CAUSE_SEPARATOR = ": "
CAUSE_CODE_MAX_CHARS = 64
CAUSE_CODE_PATTERN = r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+"

CAUSE_UNCLASSIFIED = "unclassified"
CAUSE_INVALID_JSON = "invalid_json"
CAUSE_ARTIFACT_STAGING_INCOMPLETE = "artifact_staging_incomplete"
CAUSE_TRANSLATIONS_REQUIRED = "translations_required"

__all__ = [
    "CAUSE_ARTIFACT_STAGING_INCOMPLETE",
    "CAUSE_CODE_MAX_CHARS",
    "CAUSE_CODE_PATTERN",
    "CAUSE_INVALID_JSON",
    "CAUSE_SEPARATOR",
    "CAUSE_TRANSLATIONS_REQUIRED",
    "CAUSE_UNCLASSIFIED",
]
