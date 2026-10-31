"""Unit tests for the coded HTTP error handler.

Gherkin: tests/features/admin_error_codes_ae0514.feature
"""

import json

import pytest
from fastapi import Request

from rag_backend.api.middleware.coded_error_handler import (
    CodedHTTPException,
    coded_error_handler,
)

_DETAIL = "User account is deactivated"
_CODE = "user_inactive"


def _request() -> Request:
    """A bare HTTP request scope for the handler."""
    return Request(scope={"type": "http", "method": "POST", "path": "/x"})


class TestCodedErrorHandler:
    """Scenario: A deactivated account cannot sign in and gets the inactive code."""

    def test_body_keeps_detail_and_adds_code(self) -> None:
        response = coded_error_handler(
            _request(), CodedHTTPException(401, _DETAIL, _CODE)
        )

        assert response.status_code == 401
        assert json.loads(bytes(response.body)) == {"detail": _DETAIL, "code": _CODE}

    def test_is_still_an_http_exception(self) -> None:
        error = CodedHTTPException(409, _DETAIL, _CODE)

        assert error.status_code == 409
        assert error.detail == _DETAIL
        assert error.code == _CODE

    def test_reraises_any_other_exception(self) -> None:
        with pytest.raises(ValueError, match="boom"):
            coded_error_handler(_request(), ValueError("boom"))


class TestCodedErrorsInOpenApi:
    """Scenario: A duplicate email on create returns the email-exists code."""

    @pytest.mark.parametrize(
        ("path", "method", "status", "schema"),
        [
            ("/api/admin/users", "post", "409", "CodedErrorResponse"),
            ("/api/admin/users/{user_id}", "patch", "409", "CodedErrorResponse"),
            ("/api/admin/users/{user_id}", "delete", "409", "CodedErrorResponse"),
            ("/api/auth/token", "post", "401", "LoginErrorResponse"),
        ],
    )
    def test_the_coded_response_is_documented(
        self, path: str, method: str, status: str, schema: str
    ) -> None:
        from rag_backend.api.app import create_app

        document = create_app().openapi()
        response = document["paths"][path][method]["responses"][status]
        ref = response["content"]["application/json"]["schema"]["$ref"]

        assert ref.endswith(f"/{schema}")
        assert "code" in document["components"]["schemas"][schema]["properties"]
