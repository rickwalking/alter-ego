"""API routes for persona management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.schemas.persona_rubric import (
    PersonaProfileCreate,
    PersonaProfileListResponse,
    PersonaProfileResponse,
    PersonaProfileUpdate,
)
from rag_backend.domain.constants.blog_post import (
    FORBIDDEN_PHRASE_IN_TODAYS_WORLD,
    FORBIDDEN_PHRASE_LETS_DIVE_IN,
)
from rag_backend.domain.constants.persona import DEFAULT_TONE_ATTRIBUTES
from rag_backend.infrastructure.database.models import PersonaProfileModel

router = APIRouter(tags=["personas"])


@router.post(
    "/personas",
    response_model=PersonaProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create persona",
)
async def create_persona(
    data: PersonaProfileCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> PersonaProfileResponse:
    """Create a new persona profile."""
    persona = PersonaProfileModel(
        name=data.name,
        description=data.description,
        tone_attributes=(
            data.tone_attributes.model_dump()
            if data.tone_attributes
            else DEFAULT_TONE_ATTRIBUTES
        ),
        writing_samples=data.writing_samples or [],
        forbidden_phrases=data.forbidden_phrases or [],
        preferred_phrases=data.preferred_phrases or [],
        sentence_structure_preferences=data.sentence_structure_preferences,
        paragraph_style=data.paragraph_style,
        opinion_expression=data.opinion_expression,
        expertise_areas=data.expertise_areas or [],
    )
    db.add(persona)
    await db.commit()
    await db.refresh(persona)
    return persona


@router.get(
    "/personas",
    response_model=PersonaProfileListResponse,
    summary="List personas",
)
async def list_personas(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> PersonaProfileListResponse:
    """List all persona profiles."""
    result = await db.execute(select(PersonaProfileModel))
    personas = result.scalars().all()
    return PersonaProfileListResponse(items=list(personas), total=len(personas))


@router.get(
    "/personas/{persona_id}",
    response_model=PersonaProfileResponse,
    summary="Get persona",
)
async def get_persona(
    persona_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> PersonaProfileResponse:
    """Get a specific persona profile."""
    persona = await db.get(PersonaProfileModel, str(persona_id))
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona not found: {persona_id}",
        )
    return persona


@router.put(
    "/personas/{persona_id}",
    response_model=PersonaProfileResponse,
    summary="Update persona",
)
async def update_persona(
    persona_id: UUID,
    data: PersonaProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> PersonaProfileResponse:
    """Update a persona profile."""
    persona = await db.get(PersonaProfileModel, str(persona_id))
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona not found: {persona_id}",
        )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(persona, key, value)

    await db.commit()
    await db.refresh(persona)
    return persona


@router.delete(
    "/personas/{persona_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete persona",
)
async def delete_persona(
    persona_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> None:
    """Delete a persona profile."""
    persona = await db.get(PersonaProfileModel, str(persona_id))
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona not found: {persona_id}",
        )

    await db.delete(persona)
    await db.commit()


@router.post(
    "/personas/{persona_id}/feedback",
    response_model=PersonaProfileResponse,
    summary="Add feedback to persona",
)
async def add_persona_feedback(
    persona_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    original_text: str = Query(..., min_length=1, max_length=5000),
    corrected_text: str = Query(..., min_length=1, max_length=5000),
) -> PersonaProfileResponse:
    """Add feedback to train the persona."""
    persona = await db.get(PersonaProfileModel, str(persona_id))
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona not found: {persona_id}",
        )

    persona.add_writing_sample(corrected_text)

    if FORBIDDEN_PHRASE_IN_TODAYS_WORLD in original_text:
        persona.add_forbidden_phrase(FORBIDDEN_PHRASE_IN_TODAYS_WORLD)
    if FORBIDDEN_PHRASE_LETS_DIVE_IN in original_text:
        persona.add_forbidden_phrase(FORBIDDEN_PHRASE_LETS_DIVE_IN)

    await db.commit()
    await db.refresh(persona)
    return persona
