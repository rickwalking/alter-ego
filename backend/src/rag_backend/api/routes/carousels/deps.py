from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.refinement_service import (
    CarouselRefinementConfig,
)
from rag_backend.application.services.carousel.refinement_service import (
    CarouselRefinementService as CarouselRefinementServiceImpl,
)
from rag_backend.application.services.carousel_template.strategies.registry import (
    SlideLayoutRegistry,
)
from rag_backend.domain.protocols import (
    CarouselRefinementService,
    CarouselRepository,
    SocialPublisher,
)
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import get_session


def get_carousel_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CarouselRepository:
    return PostgresCarouselRepository(session)


def get_instagram_publisher() -> SocialPublisher:
    from rag_backend.infrastructure.container import get_container

    container = get_container()
    if bool(container.instagram_publisher.overridden):
        return container.instagram_publisher()
    return container.instagram_publisher()


def get_carousel_refinement(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CarouselRefinementService:
    from rag_backend.infrastructure.container import get_container

    container = get_container()
    if bool(container.carousel_refinement.overridden):
        return container.carousel_refinement()

    config = CarouselRefinementConfig(
        repository=PostgresCarouselRepository(session),
        llm_service=container.llm_service(),
        image_registry=container.image_provider_registry(),
        export_service=container.export_service(),
        pdf_slide_builder=container.pdf_slide_builder(),
        strategy_registry=container.strategy_registry(),
    )
    return CarouselRefinementServiceImpl(config=config)


def get_strategy_registry() -> SlideLayoutRegistry:
    from rag_backend.infrastructure.container import get_container

    container = get_container()
    return container.strategy_registry()
