"""AE-0298: CarouselProjectResponse echoes custom_visual_details.

Scenario: the request-side image guidance round-trips through the project
response so the value survives a reload (see
frontend/tests/features/create-image-guidance.feature).
"""

from rag_backend.api.schemas.carousel import CarouselProjectResponse
from rag_backend.domain.models import CarouselProject, CarouselTheme


def _project(details: str | None) -> CarouselProject:
    return CarouselProject(
        topic="Agents",
        audience="Engineers",
        niche="AI",
        theme=CarouselTheme.AI_COMPETITION,
        custom_visual_details=details,
    )


class TestCarouselResponseEcho:
    def test_custom_visual_details_round_trips(self) -> None:
        response = CarouselProjectResponse.model_validate(_project("misty harbor"))
        assert response.custom_visual_details == "misty harbor"

    def test_absent_details_serialize_as_none(self) -> None:
        response = CarouselProjectResponse.model_validate(_project(None))
        assert response.custom_visual_details is None
