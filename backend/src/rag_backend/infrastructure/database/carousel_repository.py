"""PostgreSQL repository for carousel projects."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
    ResearchSource,
)
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.infrastructure.database.models import (
    CarouselProjectModel,
    CarouselSlideModel,
    ResearchSourceModel,
)


class PostgresCarouselRepository(CarouselRepository):
    """PostgreSQL implementation of CarouselRepository protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_project(self, project: CarouselProject) -> CarouselProject:
        """Create a new carousel project."""
        model = CarouselProjectModel.from_entity(project)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return model.to_entity()

    async def get_project_by_id(self, project_id: UUID) -> CarouselProject | None:
        """Get a carousel project by its ID with slides and sources."""
        stmt = select(CarouselProjectModel).where(
            CarouselProjectModel.id == str(project_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model.to_entity()

    async def get_all_projects(
        self,
        status: CarouselStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CarouselProject]:
        """Get all carousel projects with optional filtering."""
        stmt = select(CarouselProjectModel).order_by(
            CarouselProjectModel.updated_at.desc()
        )
        if status is not None:
            stmt = stmt.where(CarouselProjectModel.status == status.value)
        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model.to_entity() for model in models]

    async def update_project(self, project: CarouselProject) -> CarouselProject:
        """Update an existing carousel project."""
        stmt = select(CarouselProjectModel).where(
            CarouselProjectModel.id == str(project.id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Carousel project {project.id} not found")
        model.update_from_entity(project)
        await self._session.commit()
        await self._session.refresh(model)
        return model.to_entity()

    async def delete_project(self, project_id: UUID) -> bool:
        """Delete a carousel project and its slides."""
        stmt = select(CarouselProjectModel).where(
            CarouselProjectModel.id == str(project_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.commit()
        return True

    async def create_slide(self, slide: CarouselSlide) -> CarouselSlide:
        """Create a new carousel slide."""
        model = CarouselSlideModel.from_entity(slide)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return model.to_entity()

    async def get_slides_by_project(self, project_id: UUID) -> list[CarouselSlide]:
        """Get all slides for a project ordered by slide_number."""
        stmt = (
            select(CarouselSlideModel)
            .where(CarouselSlideModel.project_id == str(project_id))
            .order_by(CarouselSlideModel.slide_number)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model.to_entity() for model in models]

    async def update_slide(self, slide: CarouselSlide) -> CarouselSlide:
        """Update an existing carousel slide."""
        stmt = select(CarouselSlideModel).where(
            CarouselSlideModel.id == str(slide.id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Carousel slide {slide.id} not found")
        model.update_from_entity(slide)
        await self._session.commit()
        await self._session.refresh(model)
        return model.to_entity()

    async def delete_slides_by_project(self, project_id: UUID) -> bool:
        """Delete all slides for a project."""
        stmt = select(CarouselSlideModel).where(
            CarouselSlideModel.project_id == str(project_id)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        if not models:
            return False
        for model in models:
            await self._session.delete(model)
        await self._session.flush()
        return True

    async def create_research_source(self, source: ResearchSource) -> ResearchSource:
        """Create a new research source."""
        model = ResearchSourceModel.from_entity(source)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_entity()

    async def get_sources_by_project(self, project_id: UUID) -> list[ResearchSource]:
        """Get all research sources for a project."""
        stmt = (
            select(ResearchSourceModel)
            .where(ResearchSourceModel.project_id == str(project_id))
            .order_by(ResearchSourceModel.created_at)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [model.to_entity() for model in models]

    async def count(self, status: CarouselStatus | None = None) -> int:
        """Count carousel projects with optional status filter."""
        stmt = select(func.count(CarouselProjectModel.id))
        if status is not None:
            stmt = stmt.where(CarouselProjectModel.status == status.value)
        result = await self._session.execute(stmt)
        return result.scalar_one()
