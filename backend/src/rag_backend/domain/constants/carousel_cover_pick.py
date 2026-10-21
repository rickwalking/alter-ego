"""Constants for the publish-step slide-1 cover picker.

The owner of a finished Ponto de Vista carousel swaps slide 1's photo for
another photo of their library (role ``hook``) or for the autopilot run's
GrokBot cover offer. The error codes are the public API contract.
"""

from __future__ import annotations

COVER_SOURCE_LIBRARY = "library"
COVER_SOURCE_OFFER = "offer"

COVER_PICK_STATUS_SWITCHED = "switched"

ERR_COVER_PICK_NOT_POV = "cover_pick_not_pov"
ERR_COVER_PICK_NOT_COMPLETED = "cover_pick_not_completed"
ERR_COVER_PICK_ASSET_NOT_ALLOWED = "cover_pick_asset_not_allowed"

__all__ = [
    "COVER_PICK_STATUS_SWITCHED",
    "COVER_SOURCE_LIBRARY",
    "COVER_SOURCE_OFFER",
    "ERR_COVER_PICK_ASSET_NOT_ALLOWED",
    "ERR_COVER_PICK_NOT_COMPLETED",
    "ERR_COVER_PICK_NOT_POV",
]
