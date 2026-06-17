"""PostgreSQL repository for carousel projects."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models import (
    CarouselImageGeneration,
    CarouselProject,
    CarouselSlide,
    CarouselStatus,
    ResearchSource,
)
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.domain.protocols.repositories import _ProjectQuery
from rag_backend.infrastructure.database.carousel_blog_dual_write import (
    sync_carousel_blog_post,
)
from rag_backend.infrastructure.database.distribution_home import (
    DISTRIBUTION_CAPTION_KEY,
    DISTRIBUTION_LINKEDIN_POST_EN_KEY,
    DISTRIBUTION_LINKEDIN_POST_PT_KEY,
    read_distribution,
)
from rag_backend.infrastructure.database.models import (
    CarouselImageGenerationModel,
    CarouselProjectModel,
    CarouselSlideModel,
    ResearchSourceModel,
)
from rag_backend.infrastructure.database.models.carousel_creator_asset import (
    CarouselCreatorAssetModel,
)

_ERR_PROJECT_NOT_FOUND = "Carousel project {} not found"
_ERR_SLIDE_NOT_FOUND = "Carousel slide {} not found"


class PostgresCarouselRepository(CarouselRepository):
    """PostgreSQL implementation of CarouselRepository protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_project(self, project: CarouselProject) -> CarouselProject:
        """Create a new carousel project."""
        model = CarouselProjectModel.from_entity(project)
        self._session.add(model)
        await self._session.flush()
        await sync_carousel_blog_post(self._session, project)
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
        entity = model.to_entity()
        if model.creator_asset_id:
            asset_model = await self._session.get(
                CarouselCreatorAssetModel,
                str(model.creator_asset_id),
            )
            if asset_model is not None:
                entity.creator_asset_staged_path = asset_model.relative_path
        await self._overlay_distribution(entity)
        return entity

    async def _overlay_distribution(self, entity: CarouselProject) -> None:
        """Source the distribution copy from the canonical home (AE-0204).

        Overlays ``caption`` / ``linkedin_post_pt`` / ``linkedin_post_en`` on a
        freshly-loaded carousel entity from the canonical
        ``blog_posts.distribution`` home so every reader that consumes a project
        loaded through this repository sources those three fields from the
        canonical home — the embedded ORM columns are read-dead. When no
        carousel-origin row exists yet (no canonical home), the entity keeps its
        ORM-mapped defaults so behavior is byte-identical for un-backfilled rows.
        """
        distribution = await read_distribution(self._session, str(entity.id))
        if distribution is None:
            return
        entity.caption = distribution[DISTRIBUTION_CAPTION_KEY]
        entity.linkedin_post_pt = distribution[DISTRIBUTION_LINKEDIN_POST_PT_KEY]
        entity.linkedin_post_en = distribution[DISTRIBUTION_LINKEDIN_POST_EN_KEY]

    async def get_all_projects(
        self,
        *,
        query: _ProjectQuery,
    ) -> list[CarouselProject]:
        """Get all carousel projects with optional filtering."""
        stmt = select(CarouselProjectModel).order_by(
            CarouselProjectModel.updated_at.desc()
        )
        status = query.get("status")
        if status is not None:
            stmt = stmt.where(CarouselProjectModel.status == status.value)
        if query.get("public_only"):
            stmt = stmt.where(CarouselProjectModel.is_public.is_(True))
        owner_id = query.get("owner_id")
        if owner_id is not None:
            stmt = stmt.where(CarouselProjectModel.owner_id == owner_id)
        stmt = stmt.limit(query.get("limit", 100)).offset(query.get("offset", 0))
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
            raise ValueError(_ERR_PROJECT_NOT_FOUND.format(project.id))
        model.update_from_entity(project)
        await self._session.flush()
        await sync_carousel_blog_post(self._session, project)
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
        await self._session.flush()
        await self._session.commit()
        return True

    async def create_slide(self, slide: CarouselSlide) -> CarouselSlide:
        """Create a new carousel slide."""
        model = CarouselSlideModel.from_entity(slide)
        self._session.add(model)
        await self._session.flush()
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
        stmt = select(CarouselSlideModel).where(CarouselSlideModel.id == str(slide.id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(_ERR_SLIDE_NOT_FOUND.format(slide.id))
        model.update_from_entity(slide)
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(model)
        return model.to_entity()

    async def get_image_generation_by_key(
        self,
        generation_key: str,
    ) -> CarouselImageGeneration | None:
        """Get an image generation attempt by deterministic key."""
        stmt = select(CarouselImageGenerationModel).where(
            CarouselImageGenerationModel.generation_key == generation_key
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_entity() if model is not None else None

    async def upsert_image_generation(
        self,
        generation: CarouselImageGeneration,
    ) -> CarouselImageGeneration:
        """Create or update an image generation attempt by generation key."""
        stmt = select(CarouselImageGenerationModel).where(
            CarouselImageGenerationModel.generation_key == generation.generation_key
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            model = CarouselImageGenerationModel.from_entity(generation)
            self._session.add(model)
        else:
            model.update_from_entity(generation)
        await self._session.flush()
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
        await self._session.commit()
        return True

    async def create_research_source(self, source: ResearchSource) -> ResearchSource:
        """Create a new research source."""
        model = ResearchSourceModel.from_entity(source)
        self._session.add(model)
        await self._session.flush()
        await self._session.commit()
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

    async def count(
        self,
        status: CarouselStatus | None = None,
        *,
        public_only: bool = False,
        owner_id: str | None = None,
    ) -> int:
        """Count carousel projects with optional filters."""
        stmt = select(func.count(CarouselProjectModel.id))
        if status is not None:
            stmt = stmt.where(CarouselProjectModel.status == status.value)
        if public_only:
            stmt = stmt.where(CarouselProjectModel.is_public.is_(True))
        if owner_id is not None:
            stmt = stmt.where(CarouselProjectModel.owner_id == owner_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()
