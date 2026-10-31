"""Error bodies that carry a stable machine-readable ``code`` (OpenAPI docs).

The handler in ``api.middleware.coded_error_handler`` writes these shapes; the
models only describe them in the OpenAPI document.
"""

from pydantic import BaseModel


class CodedErrorResponse(BaseModel):
    """An error with its legacy English ``detail`` and a stable ``code``."""

    detail: str
    code: str


class LoginErrorResponse(BaseModel):
    """A failed sign-in; ``code`` is ``user_inactive`` for a deactivated account."""

    detail: str
    code: str | None = None


__all__ = ["CodedErrorResponse", "LoginErrorResponse"]
