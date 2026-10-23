"""Domain model of an image bridge job.

Private to the module. A job is one image request sent to the Grok Bot. It
is ``pending`` until the callback records an image (``succeeded``) or an
error (``failed``), or until the waiter gives up (``expired``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from rag_backend.modules.image_bridge.constants import (
    CONTENT_TYPE_CAROUSEL,
    ERR_INVALID_SIZE,
    FIELD_B64_JSON,
    FIELD_CALLBACK_TOKEN,
    FIELD_CALLBACK_URL,
    FIELD_CONTENT_TYPE,
    FIELD_EXPIRES_AT,
    FIELD_JOB_ID,
    FIELD_METADATA,
    FIELD_MIME_TYPE,
    FIELD_MODEL,
    FIELD_N,
    FIELD_PROJECT_ID,
    FIELD_PROMPT,
    FIELD_REFERENCE_IMAGES,
    FIELD_RESPONSE_FORMAT,
    FIELD_SIZE,
    FIELD_TASK,
    IMAGE_COUNT,
    RESPONSE_FORMAT_B64_JSON,
    SIZE_SEPARATOR,
)

_ISO_UTC_SUFFIX = "Z"
_ISO_UTC_OFFSET = "+00:00"


class ImageBridgeJobStatus(StrEnum):
    """Lifecycle of a bridge job. Only ``pending`` accepts a callback."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass(frozen=True)
class ImageBridgeJob:
    """One bridge job row, without the image bytes."""

    id: UUID
    status: ImageBridgeJobStatus
    size: str
    token_sha256: str
    created_at: datetime
    expires_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None

    def is_overdue(self, now: datetime) -> bool:
        """True once the job's deadline has passed."""
        return now >= self.expires_at


@dataclass(frozen=True)
class JobSuccess:
    """Record the decoded image of a pending job."""

    job_id: UUID
    image: bytes
    at: datetime


@dataclass(frozen=True)
class JobFailure:
    """Record why a pending job failed."""

    job_id: UUID
    code: str
    message: str
    at: datetime


@dataclass(frozen=True)
class JobDeadline:
    """Expire a pending job whose deadline passed."""

    job_id: UUID
    at: datetime


@dataclass(frozen=True)
class WebhookReference:
    """One reference image of an image-edit job (contract section 2.4)."""

    b64_json: str
    mime_type: str

    def payload(self) -> dict[str, str]:
        """The JSON object of one entry of ``reference_images``."""
        return {FIELD_B64_JSON: self.b64_json, FIELD_MIME_TYPE: self.mime_type}


@dataclass(frozen=True)
class WebhookRequest:
    """The outbound webhook body of contract section 2.1.

    An image-edit job (section 2.4) also carries ``task`` and its
    ``reference_images``; a text-only job sends neither key.
    """

    job_id: UUID
    model: str
    prompt: str
    size: str
    callback_url: str
    callback_token: str
    expires_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)
    task: str = ""
    reference_images: tuple[WebhookReference, ...] = ()

    def payload(self) -> dict[str, object]:
        """JSON body sent to the Grok Bot webhook."""
        body = self._base_payload()
        if self.task:
            body[FIELD_TASK] = self.task
        if self.reference_images:
            body[FIELD_REFERENCE_IMAGES] = [
                reference.payload() for reference in self.reference_images
            ]
        return body

    def _base_payload(self) -> dict[str, object]:
        return {
            FIELD_JOB_ID: str(self.job_id),
            FIELD_MODEL: self.model,
            FIELD_PROMPT: self.prompt,
            FIELD_SIZE: self.size,
            FIELD_N: IMAGE_COUNT,
            FIELD_RESPONSE_FORMAT: RESPONSE_FORMAT_B64_JSON,
            FIELD_CALLBACK_URL: self.callback_url,
            FIELD_CALLBACK_TOKEN: self.callback_token,
            FIELD_EXPIRES_AT: _iso_utc(self.expires_at),
            FIELD_METADATA: dict(self.metadata),
        }


def job_metadata(
    project_id: str | None, content_type: str = CONTENT_TYPE_CAROUSEL
) -> dict[str, str]:
    """Webhook metadata: the content type, plus the project when known."""
    metadata = {FIELD_CONTENT_TYPE: content_type}
    if project_id:
        metadata[FIELD_PROJECT_ID] = project_id
    return metadata


def _iso_utc(moment: datetime) -> str:
    return moment.isoformat().replace(_ISO_UTC_OFFSET, _ISO_UTC_SUFFIX)


@dataclass(frozen=True)
class ImageSize:
    """A ``WIDTHxHEIGHT`` image size."""

    width: int
    height: int

    @classmethod
    def parse(cls, text: str) -> ImageSize:
        """Parse ``"1536x1024"``; raise ``ValueError`` on anything else."""
        width, sep, height = text.strip().lower().partition(SIZE_SEPARATOR)
        if not sep or not width.isdigit() or not height.isdigit():
            raise ValueError(ERR_INVALID_SIZE.format(size=text))
        return cls(width=int(width), height=int(height))
