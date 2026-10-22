"""Public carousel feed projection and view rules.

Gherkin: tests/features/public_carousel_list_redaction_ae0452.feature
"""

from __future__ import annotations

from uuid import uuid4

from rag_backend.api.routes.carousels.public_feed import (
    is_public_feed_view,
    public_feed_item,
    public_feed_status,
)
from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
    CarouselTheme,
    User,
)
from rag_backend.domain.models.user import UserRole


def _user(role: UserRole) -> User:
    return User(
        email=f"{role.value}@example.com",
        full_name="Viewer",
        role=role,
        hashed_password="x",
    )


def _project() -> CarouselProject:
    project = CarouselProject(
        topic="Topic",
        audience="Devs",
        niche="AI",
        title="Public title",
        theme=CarouselTheme.AI_COMPETITION,
        blog_markdown="# Draft",
        output_dir="/srv/out",
    )
    project.slides = [
        CarouselSlide(
            project_id=project.id,
            slide_number=1,
            slide_type="content",
            heading="Heading",
            body="Body",
            image_path="/srv/out/slide_1.jpg",
        )
    ]
    return project


def test_public_feed_item_drops_slides_and_private_fields() -> None:
    # Scenario: A public feed item never carries slide image paths
    item = public_feed_item(_project())

    assert item.slides == []
    assert item.blog_markdown is None
    assert item.output_dir is None
    assert item.title == "Public title"


def test_public_view_rules() -> None:
    # Scenario: An admin browsing the public feed still sees the full project
    editor = _user(UserRole.EDITOR)
    admin = _user(UserRole.ADMIN)

    assert is_public_feed_view(None, public_only=None) is True
    assert is_public_feed_view(editor, public_only=True) is True
    assert is_public_feed_view(editor, public_only=None) is False
    assert is_public_feed_view(admin, public_only=True) is False


def test_public_view_forces_completed_status() -> None:
    # Scenario: A signed-in editor browsing the public feed never lists an unfinished carousel
    assert (
        public_feed_status(CarouselStatus.FAILED, public_view=True)
        == CarouselStatus.COMPLETED
    )
    assert public_feed_status(None, public_view=True) == CarouselStatus.COMPLETED
    assert (
        public_feed_status(CarouselStatus.FAILED, public_view=False)
        == CarouselStatus.FAILED
    )
    assert public_feed_status(None, public_view=False) is None


def test_projection_keeps_project_identity() -> None:
    project = _project()
    project.id = uuid4()

    assert public_feed_item(project).id == project.id
