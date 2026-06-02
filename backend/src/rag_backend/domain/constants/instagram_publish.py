"""Stable error codes for Instagram publish failures returned to clients."""

ERR_INSTAGRAM_API_REQUEST_FAILED = "instagram_api_request_failed"
ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED = "instagram_credentials_not_configured"
ERR_INSTAGRAM_IMAGE_COUNT_INVALID = "instagram_image_count_invalid"
ERR_INSTAGRAM_CONTAINER_FAILED = "instagram_container_failed"
ERR_INSTAGRAM_CONTAINER_TIMEOUT = "instagram_container_timeout"
ERR_INSTAGRAM_API_NO_ID = "instagram_api_no_id"

__all__ = [
    "ERR_INSTAGRAM_API_NO_ID",
    "ERR_INSTAGRAM_API_REQUEST_FAILED",
    "ERR_INSTAGRAM_CONTAINER_FAILED",
    "ERR_INSTAGRAM_CONTAINER_TIMEOUT",
    "ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED",
    "ERR_INSTAGRAM_IMAGE_COUNT_INVALID",
]
