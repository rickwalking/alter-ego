"""Vulture whitelist for intentional unused code."""

# Protocol parameters that are part of interface contract but not yet used
# Vulture strips leading underscores, so we whitelist both forms
source_types
_source_types
