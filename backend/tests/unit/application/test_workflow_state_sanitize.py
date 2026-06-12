"""Unit tests for workflow state copy sanitization."""

from rag_backend.application.services.carousel.workflow_state_sanitize import (
    SanitizeWorkflowStateCommand,
    sanitize_outline_slides,
    sanitize_workflow_state_artifacts,
)


class TestWorkflowStateSanitize:
    def test_sanitize_outline_resolves_bilingual_titles(self) -> None:
        outline = sanitize_outline_slides([
            {
                "slide_index": 1,
                "title": "{'pt': 'Título PT', 'en': 'Title EN'}",
                "key_points": [],
            }
        ])
        assert outline[0]["title"] == "Título PT"

    def test_sanitize_workflow_state_rebuilds_validation(self) -> None:
        state = sanitize_workflow_state_artifacts(
            SanitizeWorkflowStateCommand(
                state={
                    "outline": [
                        {
                            "slide_index": 1,
                            "title": "{'pt': 'Hook', 'en': 'Hook EN'}",
                            "key_points": [],
                        }
                    ],
                    "slide_drafts": [
                        {
                            "slide_index": 1,
                            "slide_type": "intro",
                            "presentation_pt": {
                                "slide_type": "intro",
                                "heading": "Hook",
                                "body": "Subtítulo curto.",
                            },
                            "presentation_en": {
                                "slide_type": "intro",
                                "heading": "Hook",
                                "body": "Short subtitle.",
                            },
                        }
                    ],
                }
            ),
        )
        assert state["outline"][0]["title"] == "Hook"
        validation = state.get("presentation_validation")
        assert isinstance(validation, dict)
        assert validation.get("validation_status") == "valid"
