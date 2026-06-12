"""Phase 5 data migration service (MIG-001-MIG-004)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.blog_post import DEFAULT_FORBIDDEN_PHRASES
from rag_backend.domain.constants.carousel import (
    CAROUSEL_STATUS_COMPLETED,
    CAROUSEL_STATUS_DESIGNING,
    CAROUSEL_STATUS_DRAFTING,
    CAROUSEL_STATUS_EXPORTING,
    CAROUSEL_STATUS_FAILED,
    CAROUSEL_STATUS_GENERATING_IMAGES,
    CAROUSEL_STATUS_PENDING,
    CAROUSEL_STATUS_RESEARCHING,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_PUBLISHED,
    PHASE_RESEARCH,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_PENDING,
    PHASE_STATUS_REJECTED,
)
from rag_backend.domain.constants.migration import (
    BRIEF_FIELD_AUDIENCE,
    BRIEF_FIELD_IMAGE_STYLE,
    BRIEF_FIELD_INSTRUCTIONS,
    BRIEF_FIELD_LANGUAGE,
    BRIEF_FIELD_NICHE,
    BRIEF_FIELD_SLIDES,
    BRIEF_FIELD_SUBTITLE,
    BRIEF_FIELD_THEME,
    BRIEF_FIELD_TITLE,
    BRIEF_FIELD_TOPIC,
    CONTENT_TYPE_BLOG_POST,
    CONTENT_TYPE_CAROUSEL,
    CRITERION_CLARITY,
    CRITERION_ENGAGEMENT,
    CRITERION_ORIGINALITY,
    CRITERION_VOICE_MATCH,
    DEFAULT_PERSONA_DESCRIPTION,
    DEFAULT_PERSONA_EXPERTISE,
    DEFAULT_PERSONA_NAME,
    DEFAULT_RUBRIC_DESCRIPTION,
    DEFAULT_RUBRIC_NAME,
    ERR_NO_WRITING_SAMPLES,
    MAX_SAMPLE_LENGTH,
    MAX_WRITING_SAMPLES,
)
from rag_backend.domain.constants.persona import DEFAULT_TONE_ATTRIBUTES
from rag_backend.domain.models.rubric import EvaluationMethod, ScoringScale
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.persona_rubric import (
    PersonaProfileModel,
    QualityRubricModel,
)

STATUS_TO_WORKFLOW: dict[str, tuple[str, str]] = {
    CAROUSEL_STATUS_PENDING: (PHASE_BRIEF, PHASE_STATUS_PENDING),
    CAROUSEL_STATUS_RESEARCHING: (PHASE_RESEARCH, PHASE_STATUS_IN_PROGRESS),
    CAROUSEL_STATUS_DRAFTING: (PHASE_OUTLINE, PHASE_STATUS_IN_PROGRESS),
    CAROUSEL_STATUS_DESIGNING: (PHASE_DESIGN, PHASE_STATUS_IN_PROGRESS),
    CAROUSEL_STATUS_GENERATING_IMAGES: (PHASE_IMAGES, PHASE_STATUS_IN_PROGRESS),
    CAROUSEL_STATUS_EXPORTING: (PHASE_FINAL_REVIEW, PHASE_STATUS_IN_PROGRESS),
    CAROUSEL_STATUS_COMPLETED: (PHASE_PUBLISHED, PHASE_STATUS_APPROVED),
    CAROUSEL_STATUS_FAILED: (PHASE_BRIEF, PHASE_STATUS_REJECTED),
}


@dataclass
class Phase5MigrationReport:
    """Summary of a Phase 5 migration run."""

    creative_briefs_updated: int = 0
    persona_created: bool = False
    persona_id: str | None = None
    rubric_created: bool = False
    rubric_id: str | None = None
    workflow_states_updated: int = 0
    projects_linked: int = 0
    dry_run: bool = False
    errors: list[str] = field(default_factory=list)


def build_creative_brief(project: CarouselProjectModel) -> str:
    """Build creative_brief from legacy carousel project fields (MIG-001)."""
    sections: list[str] = []
    field_map = (
        (BRIEF_FIELD_TOPIC, project.topic),
        (BRIEF_FIELD_AUDIENCE, project.audience),
        (BRIEF_FIELD_NICHE, project.niche),
        (BRIEF_FIELD_TITLE, project.title),
        (BRIEF_FIELD_SUBTITLE, project.subtitle),
        (BRIEF_FIELD_SLIDES, project.slides_config),
        (BRIEF_FIELD_LANGUAGE, project.language),
        (BRIEF_FIELD_THEME, project.theme),
        (BRIEF_FIELD_IMAGE_STYLE, project.image_style),
    )
    for label, value in field_map:
        if value:
            sections.append(f"**{label}:** {value}")
    if project.instructions:
        sections.append(f"**{BRIEF_FIELD_INSTRUCTIONS}:** {project.instructions}")
    return "\n\n".join(sections)


def _default_rubric_criteria() -> list[dict[str, object]]:
    """Standard editorial rubric criteria (MIG-003)."""
    return [
        {
            "id": f"{CRITERION_ORIGINALITY}_criterion",
            "name": "Originality",
            "description": "Content is original and not overly derivative of sources.",
            "weight": 0.25,
            "evaluation_method": EvaluationMethod.AI_AUTO.value,
            "min_threshold": 70.0,
            "scoring_scale": ScoringScale.SCORE_0_100.value,
            "prompt_template": "Rate originality of the content from 0-100.",
        },
        {
            "id": f"{CRITERION_VOICE_MATCH}_criterion",
            "name": "Voice Match",
            "description": "Content matches the assigned persona voice.",
            "weight": 0.25,
            "evaluation_method": EvaluationMethod.HYBRID.value,
            "min_threshold": 70.0,
            "scoring_scale": ScoringScale.SCORE_0_100.value,
            "prompt_template": "Rate how well the content matches the persona voice.",
        },
        {
            "id": f"{CRITERION_ENGAGEMENT}_criterion",
            "name": "Engagement",
            "description": "Content hooks the reader and maintains interest.",
            "weight": 0.25,
            "evaluation_method": EvaluationMethod.AI_AUTO.value,
            "min_threshold": 65.0,
            "scoring_scale": ScoringScale.SCORE_0_100.value,
            "prompt_template": "Rate engagement potential from 0-100.",
        },
        {
            "id": f"{CRITERION_CLARITY}_criterion",
            "name": "Clarity",
            "description": "Content is clear, structured, and easy to follow.",
            "weight": 0.25,
            "evaluation_method": EvaluationMethod.AI_AUTO.value,
            "min_threshold": 70.0,
            "scoring_scale": ScoringScale.SCORE_0_100.value,
            "prompt_template": "Rate clarity and structure from 0-100.",
        },
    ]


def _collect_writing_samples(projects: list[CarouselProjectModel]) -> list[str]:
    """Extract writing samples from completed carousel outputs (MIG-002)."""
    samples: list[str] = []
    for project in projects:
        if project.status != CAROUSEL_STATUS_COMPLETED:
            continue
        for candidate in (
            project.caption,
            project.linkedin_post_pt,
            project.linkedin_post_en,
            project.blog_markdown,
        ):
            if not candidate or not candidate.strip():
                continue
            trimmed = candidate.strip()[:MAX_SAMPLE_LENGTH]
            if trimmed not in samples:
                samples.append(trimmed)
            if len(samples) >= MAX_WRITING_SAMPLES:
                return samples
    return samples


class Phase5MigrationService:
    """Migrates legacy carousel projects to the editorial workflow schema."""

    async def run(
        self, db: AsyncSession, *, dry_run: bool = False
    ) -> Phase5MigrationReport:
        """Execute all Phase 5 migration steps."""
        report = Phase5MigrationReport(dry_run=dry_run)
        projects = await self._load_projects(db)

        persona_id = await self._ensure_default_persona(db, projects, report)
        rubric_id = await self._ensure_default_rubric(db, report)

        for project in projects:
            self._migrate_creative_brief(project, report)
            self._backfill_workflow_state(project, report)
            linked = False
            if persona_id and not project.persona_id:
                project.persona_id = persona_id
                linked = True
            if rubric_id and not project.rubric_id:
                project.rubric_id = rubric_id
                linked = True
            if linked:
                report.projects_linked += 1

        if not dry_run:
            await db.commit()
        else:
            await db.rollback()

        return report

    @staticmethod
    async def _load_projects(db: AsyncSession) -> list[CarouselProjectModel]:
        result = await db.execute(select(CarouselProjectModel))
        return list(result.scalars().all())

    @staticmethod
    def _migrate_creative_brief(
        project: CarouselProjectModel, report: Phase5MigrationReport
    ) -> None:
        if project.creative_brief:
            return
        brief = build_creative_brief(project)
        if not brief:
            return
        project.creative_brief = brief
        report.creative_briefs_updated += 1

    @staticmethod
    def _backfill_workflow_state(
        project: CarouselProjectModel, report: Phase5MigrationReport
    ) -> None:
        if (
            project.current_phase
            and project.current_phase != PHASE_BRIEF
            and project.phase_status
            and project.phase_status != PHASE_STATUS_PENDING
        ):
            return
        phase, phase_status = STATUS_TO_WORKFLOW.get(
            project.status, (PHASE_BRIEF, PHASE_STATUS_PENDING)
        )
        if project.status == CAROUSEL_STATUS_FAILED and project.error_message:
            phase = PHASE_RESEARCH if project.phase_progress else PHASE_BRIEF
        project.current_phase = phase
        project.phase_status = phase_status
        report.workflow_states_updated += 1

    @staticmethod
    async def _ensure_default_persona(
        db: AsyncSession,
        projects: list[CarouselProjectModel],
        report: Phase5MigrationReport,
    ) -> str | None:
        existing = await db.execute(
            select(PersonaProfileModel).where(
                PersonaProfileModel.name == DEFAULT_PERSONA_NAME
            )
        )
        found = existing.scalar_one_or_none()
        if found:
            report.persona_id = str(found.id)
            return str(found.id)

        samples = _collect_writing_samples(projects)
        if not samples:
            report.errors.append(ERR_NO_WRITING_SAMPLES)
            return None

        persona = PersonaProfileModel(
            name=DEFAULT_PERSONA_NAME,
            description=DEFAULT_PERSONA_DESCRIPTION,
            tone_attributes=DEFAULT_TONE_ATTRIBUTES,
            writing_samples=samples,
            forbidden_phrases=list(DEFAULT_FORBIDDEN_PHRASES),
            preferred_phrases=[],
            expertise_areas=list(DEFAULT_PERSONA_EXPERTISE),
        )
        db.add(persona)
        await db.flush()
        report.persona_created = True
        report.persona_id = str(persona.id)
        return str(persona.id)

    @staticmethod
    async def _ensure_default_rubric(
        db: AsyncSession, report: Phase5MigrationReport
    ) -> str | None:
        existing = await db.execute(
            select(QualityRubricModel).where(QualityRubricModel.is_default.is_(True))
        )
        found = existing.scalar_one_or_none()
        if found:
            report.rubric_id = str(found.id)
            return str(found.id)

        rubric = QualityRubricModel(
            name=DEFAULT_RUBRIC_NAME,
            description=DEFAULT_RUBRIC_DESCRIPTION,
            criteria=_default_rubric_criteria(),
            applicable_content_types=[CONTENT_TYPE_CAROUSEL, CONTENT_TYPE_BLOG_POST],
            is_default=True,
        )
        db.add(rubric)
        await db.flush()
        report.rubric_created = True
        report.rubric_id = str(rubric.id)
        return str(rubric.id)


__all__ = [
    "STATUS_TO_WORKFLOW",
    "Phase5MigrationReport",
    "Phase5MigrationService",
    "build_creative_brief",
]
