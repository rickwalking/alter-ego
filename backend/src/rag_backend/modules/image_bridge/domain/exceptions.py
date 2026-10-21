"""Exceptions of the image bridge module.

``ImageBridgeJobError`` is a ``RuntimeError`` so a bridge failure keeps the
contract of ``OpenAIImageService``: the images phase sees a ``RuntimeError``
and runs its existing retry/escalation path.
"""

from __future__ import annotations


class ImageBridgeJobError(RuntimeError):
    """A bridge job failed, expired or could not be started."""


class WebhookDeliveryError(RuntimeError):
    """The Grok Bot webhook did not accept the job (non-2xx or transport)."""


class MalformedCallbackError(ValueError):
    """The callback body is neither an ImagesResponse nor an OpenAI error."""


class InvalidCallbackImageError(ValueError):
    """The callback image failed decoding or validation."""


class ImageBridgeConfigError(RuntimeError):
    """The bridge is enabled without the settings it needs."""
