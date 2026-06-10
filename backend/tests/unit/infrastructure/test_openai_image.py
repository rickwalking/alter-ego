"""Unit tests for OpenAI image error extraction and structured detail reporting.

Feature: Image provider error visibility

  Scenario: OpenAI invalid model error is captured with all fields
    Given OpenAI returns an invalid model error with status, type, code, param, and message
    When _openai_status_error_detail processes the error
    Then the result includes status, type, code, param, and message

  Scenario: Error logs do not include API keys
    Given an OpenAI APIStatusError
    When _openai_status_error_detail extracts details
    Then the result dict does not contain the API key
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rag_backend.infrastructure.external.openai_image import (
    _json_error_fields,
    _openai_status_error_detail,
)


def _make_api_status_error(
    status_code: int = 400,
    body: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    """Create a mock APIStatusError for testing."""
    exc = MagicMock()
    exc.status_code = status_code
    exc.request_id = None

    response = MagicMock()
    response.headers = headers or {}
    if body is not None:
        response.json.return_value = body
    else:
        response.json.side_effect = ValueError("no JSON")

    exc.response = response
    return exc


@pytest.mark.unit
class TestJsonErrorFields:
    def test_extracts_type_code_param_and_message(self) -> None:
        payload = {
            "error": {
                "type": "invalid_request_error",
                "code": "model_not_found",
                "param": "model",
                "message": "The model gpt-image-2 does not exist",
            }
        }
        result = _json_error_fields(payload)
        assert result["type"] == "invalid_request_error"
        assert result["code"] == "model_not_found"
        assert result["param"] == "model"
        assert result["message"] == "The model gpt-image-2 does not exist"

    def test_omits_empty_fields(self) -> None:
        payload = {
            "error": {
                "type": "invalid_request_error",
                "code": "model_not_found",
                "message": "Error occurred",
            }
        }
        result = _json_error_fields(payload)
        assert "param" not in result
        assert result["type"] == "invalid_request_error"

    def test_returns_empty_when_no_error_key(self) -> None:
        payload = {"detail": "something else"}
        result = _json_error_fields(payload)
        assert result == {}

    def test_returns_empty_when_error_is_not_mapping(self) -> None:
        payload = {"error": "string error"}
        result = _json_error_fields(payload)
        assert result == {}


@pytest.mark.unit
class TestOpenaiStatusErrorDetail:
    def test_extracts_status_code_and_request_id(self) -> None:
        exc = _make_api_status_error(
            status_code=400,
            headers={"x-request-id": "req-123"},
        )
        result = _openai_status_error_detail(exc)
        assert result["status"] == 400
        assert result["request_id"] == "req-123"

    def test_extracts_structured_fields(self) -> None:
        body = {
            "error": {
                "type": "invalid_request_error",
                "code": "model_not_found",
                "param": "model",
                "message": "The model gpt-image-2 does not exist",
            }
        }
        exc = _make_api_status_error(status_code=400, body=body)
        result = _openai_status_error_detail(exc)
        assert result["status"] == 400
        assert result["type"] == "invalid_request_error"
        assert result["code"] == "model_not_found"
        assert result["param"] == "model"
        assert result["message"] == "The model gpt-image-2 does not exist"

    def test_falls_back_to_str_when_no_body(self) -> None:
        exc = _make_api_status_error(status_code=500)
        result = _openai_status_error_detail(exc)
        assert result["status"] == 500
        assert "message" in result

    def test_no_api_key_in_result(self) -> None:
        body = {
            "error": {
                "type": "invalid_request_error",
                "code": "invalid_api_key",
                "message": "Incorrect API key provided",
            }
        }
        exc = _make_api_status_error(status_code=401, body=body)
        result = _openai_status_error_detail(exc)
        assert "sk-" not in str(result.values())

    def test_includes_param_field(self) -> None:
        body = {
            "error": {
                "type": "invalid_request_error",
                "code": "invalid_model",
                "param": "model",
                "message": "Model not found",
            }
        }
        exc = _make_api_status_error(status_code=400, body=body)
        result = _openai_status_error_detail(exc)
        assert "param" in result
        assert result["param"] == "model"
