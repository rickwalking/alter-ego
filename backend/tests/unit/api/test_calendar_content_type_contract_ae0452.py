"""The committed OpenAPI artifact publishes the calendar content types the backend sends."""

import json
from pathlib import Path

from rag_backend.api.schemas.calendar import CalendarItemResponse

_ARTIFACT_PATH = (
    Path(__file__).resolve().parents[4] / "docs" / "architecture" / "openapi.json"
)


def _artifact_content_types() -> list[str]:
    """Return the content_type enum of CalendarItemResponse in the committed artifact."""
    document = json.loads(_ARTIFACT_PATH.read_text(encoding="utf-8"))
    schema = document["components"]["schemas"]["CalendarItemResponse"]
    return sorted(schema["properties"]["content_type"]["enum"])


def test_backend_content_types_match_the_published_artifact() -> None:
    # Scenario: The backend schema matches the published OpenAPI artifact
    model_schema = CalendarItemResponse.model_json_schema()
    model_types = sorted(model_schema["properties"]["content_type"]["enum"])

    assert model_types == ["blog_post", "carousel"]
    assert model_types == _artifact_content_types()
