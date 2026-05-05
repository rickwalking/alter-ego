from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.carousel_orchestrator import CarouselAgent as CarouselAgentImpl
from rag_backend.domain.protocols import CarouselAgent, CarouselRepository, SocialPublisher
from rag_backend.infrastructure.database.carousel_repository import PostgresCarouselRepository
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


def get_carousel_agent(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CarouselAgent:
    from rag_backend.infrastructure.container import get_container

    container = get_container()
    if bool(container.carousel_agent.overridden):
        return container.carousel_agent()

    settings = container.settings()
    checkpointer = getattr(request.app.state, "carousel_checkpointer", None)
    from rag_backend.infrastructure.database.config import get_session_maker

    return CarouselAgentImpl(
        repository=PostgresCarouselRepository(session),
        llm_service=container.llm_service(),
        research_tool=container.research_tool(),
        image_registry=container.image_provider_registry(),
        export_service=container.export_service(),
        linkedin_post_generator=container.linkedin_post_generator(),
        pdf_slide_builder=container.pdf_slide_builder(),
        output_base_dir=settings.carousel_output_dir,
        checkpointer=checkpointer,
        session_maker=get_session_maker(),
        repository_factory=PostgresCarouselRepository,
    )
