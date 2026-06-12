"""Unit tests for PostgresCarouselRepository."""

from uuid import uuid4

import pytest

from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
    CarouselTheme,
    ResearchSource,
    ResearchSourceType,
)


@pytest.fixture
def sample_carousel_project():
    """Create a sample carousel project for testing."""
    return CarouselProject(
        topic="Machine Learning Basics",
        audience="Beginners",
        niche="AI Education",
        theme=CarouselTheme.AI_COMPETITION,
    )


@pytest.fixture
def sample_slide(sample_carousel_project):
    """Create a sample slide for testing."""
    return CarouselSlide(
        project_id=sample_carousel_project.id,
        slide_number=1,
        slide_type="intro",
        heading="What is Machine Learning?",
        body="Machine learning is a subset of AI...",
    )


@pytest.fixture
def sample_research_source(sample_carousel_project):
    """Create a sample research source for testing."""
    return ResearchSource(
        project_id=sample_carousel_project.id,
        source_url="https://example.com/ml-basics",
        source_type=ResearchSourceType.BLOG,
        title="ML Basics Guide",
        relevance_score=0.95,
    )


@pytest.mark.unit
class TestPostgresCarouselRepository:
    """Tests for PostgresCarouselRepository."""

    async def test_create_project(self, carousel_repository, sample_carousel_project):
        """Should create a carousel project in the database."""
        created = await carousel_repository.create_project(sample_carousel_project)

        assert created.id is not None
        assert created.topic == sample_carousel_project.topic
        assert created.audience == sample_carousel_project.audience
        assert created.status == CarouselStatus.PENDING

    async def test_get_project_by_id_existing(
        self, carousel_repository, sample_carousel_project
    ):
        """Should retrieve existing project by ID."""
        created = await carousel_repository.create_project(sample_carousel_project)

        retrieved = await carousel_repository.get_project_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.topic == created.topic

    async def test_get_project_by_id_nonexistent(self, carousel_repository):
        """Should return None for non-existent project ID."""
        retrieved = await carousel_repository.get_project_by_id(uuid4())

        assert retrieved is None

    async def test_get_all_projects_empty(self, carousel_repository):
        """Should return empty list when no projects exist."""
        projects = await carousel_repository.get_all_projects(query={})

        assert projects == []

    async def test_get_all_projects_with_data(
        self, carousel_repository, sample_carousel_project
    ):
        """Should return all created projects."""
        await carousel_repository.create_project(sample_carousel_project)

        projects = await carousel_repository.get_all_projects(query={})

        assert len(projects) == 1
        assert projects[0].topic == sample_carousel_project.topic

    async def test_get_all_projects_with_status_filter(
        self, carousel_repository, sample_carousel_project
    ):
        """Should filter projects by status."""
        project1 = await carousel_repository.create_project(sample_carousel_project)
        project1.update_status(CarouselStatus.COMPLETED)
        await carousel_repository.update_project(project1)

        project2 = CarouselProject(
            topic="Deep Learning",
            audience="Advanced",
            niche="AI",
        )
        await carousel_repository.create_project(project2)

        completed = await carousel_repository.get_all_projects(
            query={"status": CarouselStatus.COMPLETED},
        )

        assert len(completed) == 1
        assert completed[0].status == CarouselStatus.COMPLETED

    async def test_update_project(self, carousel_repository, sample_carousel_project):
        """Should update an existing project."""
        created = await carousel_repository.create_project(sample_carousel_project)

        created.title = "Optimized Title"
        created.subtitle = "A comprehensive guide"
        created.mark_completed("/output/test")

        updated = await carousel_repository.update_project(created)

        assert updated.title == "Optimized Title"
        assert updated.status == CarouselStatus.COMPLETED
        assert updated.output_dir == "/output/test"

    async def test_update_nonexistent_project(
        self, carousel_repository, sample_carousel_project
    ):
        """Should raise error when updating non-existent project."""
        project = sample_carousel_project
        project.id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            await carousel_repository.update_project(project)

    async def test_delete_project_existing(
        self, carousel_repository, sample_carousel_project
    ):
        """Should delete an existing project."""
        created = await carousel_repository.create_project(sample_carousel_project)

        deleted = await carousel_repository.delete_project(created.id)

        assert deleted is True

        retrieved = await carousel_repository.get_project_by_id(created.id)
        assert retrieved is None

    async def test_delete_project_nonexistent(self, carousel_repository):
        """Should return False when deleting non-existent project."""
        deleted = await carousel_repository.delete_project(uuid4())

        assert deleted is False

    async def test_count_projects_empty(self, carousel_repository):
        """Should return 0 when no projects exist."""
        count = await carousel_repository.count()

        assert count == 0

    async def test_count_projects_with_data(
        self, carousel_repository, sample_carousel_project
    ):
        """Should return correct project count."""
        await carousel_repository.create_project(sample_carousel_project)
        await carousel_repository.create_project(
            CarouselProject(
                topic="Deep Learning",
                audience="Advanced",
                niche="AI",
            )
        )

        count = await carousel_repository.count()

        assert count == 2

    async def test_count_projects_with_status_filter(
        self, carousel_repository, sample_carousel_project
    ):
        """Should count projects filtered by status."""
        project1 = await carousel_repository.create_project(sample_carousel_project)
        project1.update_status(CarouselStatus.COMPLETED)
        await carousel_repository.update_project(project1)

        project2 = CarouselProject(
            topic="NLP Basics",
            audience="Beginners",
            niche="AI",
        )
        await carousel_repository.create_project(project2)

        completed_count = await carousel_repository.count(
            status=CarouselStatus.COMPLETED
        )
        pending_count = await carousel_repository.count(status=CarouselStatus.PENDING)

        assert completed_count == 1
        assert pending_count == 1

    async def test_create_slide(self, carousel_repository, sample_slide):
        """Should create a slide in the database."""
        created = await carousel_repository.create_slide(sample_slide)

        assert created.id is not None
        assert created.slide_number == sample_slide.slide_number
        assert created.heading == sample_slide.heading

    async def test_get_slides_by_project(
        self, carousel_repository, sample_carousel_project, sample_slide
    ):
        """Should retrieve all slides for a project."""
        await carousel_repository.create_project(sample_carousel_project)
        await carousel_repository.create_slide(sample_slide)

        slides = await carousel_repository.get_slides_by_project(
            sample_carousel_project.id
        )

        assert len(slides) == 1
        assert slides[0].slide_number == 1

    async def test_get_slides_by_project_empty(self, carousel_repository):
        """Should return empty list for project with no slides."""
        slides = await carousel_repository.get_slides_by_project(uuid4())

        assert slides == []

    async def test_update_slide(self, carousel_repository, sample_slide):
        """Should update an existing slide."""
        created = await carousel_repository.create_slide(sample_slide)

        created.heading = "Updated Heading"
        created.body = "Updated body content"

        updated = await carousel_repository.update_slide(created)

        assert updated.heading == "Updated Heading"
        assert updated.body == "Updated body content"

    async def test_update_nonexistent_slide(self, carousel_repository, sample_slide):
        """Should raise error when updating non-existent slide."""
        slide = sample_slide
        slide.id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            await carousel_repository.update_slide(slide)

    async def test_delete_slides_by_project(
        self, carousel_repository, sample_carousel_project, sample_slide
    ):
        """Should delete all slides for a project."""
        await carousel_repository.create_project(sample_carousel_project)
        await carousel_repository.create_slide(sample_slide)

        deleted = await carousel_repository.delete_slides_by_project(
            sample_carousel_project.id
        )

        assert deleted is True

        slides = await carousel_repository.get_slides_by_project(
            sample_carousel_project.id
        )
        assert slides == []

    async def test_delete_slides_by_project_empty(self, carousel_repository):
        """Should return False when project has no slides."""
        deleted = await carousel_repository.delete_slides_by_project(uuid4())

        assert deleted is False

    async def test_create_research_source(
        self, carousel_repository, sample_research_source
    ):
        """Should create a research source in the database."""
        created = await carousel_repository.create_research_source(
            sample_research_source
        )

        assert created.id is not None
        assert created.source_url == sample_research_source.source_url
        assert created.source_type == sample_research_source.source_type

    async def test_get_sources_by_project(
        self, carousel_repository, sample_carousel_project, sample_research_source
    ):
        """Should retrieve all sources for a project."""
        await carousel_repository.create_project(sample_carousel_project)
        await carousel_repository.create_research_source(sample_research_source)

        sources = await carousel_repository.get_sources_by_project(
            sample_carousel_project.id
        )

        assert len(sources) == 1
        assert sources[0].source_url == sample_research_source.source_url

    async def test_get_sources_by_project_empty(self, carousel_repository):
        """Should return empty list for project with no sources."""
        sources = await carousel_repository.get_sources_by_project(uuid4())

        assert sources == []
