"""An HTTP error that carries a stable machine-readable ``code``.

The body keeps the legacy ``detail`` string (existing clients read it) and adds
``code``, so a client can show its own translated message without matching the
English ``detail`` text.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

CODE_FIELD = "code"
DETAIL_FIELD = "detail"


class CodedHTTPException(HTTPException):
    """An ``HTTPException`` whose JSON body also has a stable ``code``."""

    def __init__(self, status_code: int, detail: str, code: str) -> None:
        """Keep the status and ``detail`` of a plain HTTP error; add ``code``."""
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


def coded_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Serialize a :class:`CodedHTTPException` as ``{detail, code}``."""
    if not isinstance(exc, CodedHTTPException):
        raise exc
    return JSONResponse(
        status_code=exc.status_code,
        content={DETAIL_FIELD: exc.detail, CODE_FIELD: exc.code},
        headers=exc.headers,
    )


def add_coded_error_handler(app: FastAPI) -> None:
    """Register the coded HTTP error handler."""
    app.add_exception_handler(CodedHTTPException, coded_error_handler)


__all__ = [
    "CodedHTTPException",
    "add_coded_error_handler",
    "coded_error_handler",
]
