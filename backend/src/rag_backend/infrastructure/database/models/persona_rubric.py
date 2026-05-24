"""SQLAlchemy ORM models for PersonaProfile and QualityRubric entities."""

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)

from rag_backend.domain.models.persona import PersonaProfile as PersonaProfileEntity
from rag_backend.domain.models.rubric import (
    QualityRubric as QualityRubricEntity,
)
from rag_backend.domain.models.rubric import (
    RubricEvaluationScore,
)
from rag_backend.infrastructure.database.config import Base


class PersonaProfileModel(Base):
    """SQLAlchemy model for PersonaProfile entity."""

    __tablename__ = "persona_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tone_attributes = Column(
        JSON,
        default=lambda: {
            "formal": 0.3,
            "conversational": 0.8,
            "humorous": 0.4,
        },
        nullable=False,
    )
    writing_samples = Column(JSON, default=list, nullable=False)
    forbidden_phrases = Column(JSON, default=list, nullable=False)
    preferred_phrases = Column(JSON, default=list, nullable=False)
    sentence_structure_preferences = Column(Text, nullable=True)
    paragraph_style = Column(Text, nullable=True)
    opinion_expression = Column(Text, nullable=True)
    expertise_areas = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    version = Column(Integer, default=1, nullable=False)

    __table_args__ = (
        Index("idx_persona_profiles_name", "name"),
        Index("idx_persona_profiles_version", "version"),
    )

    def to_entity(self) -> PersonaProfileEntity:
        """Convert ORM model to domain entity."""
        from uuid import UUID

        return PersonaProfileEntity(
            id=UUID(self.id),
            name=self.name,
            description=self.description,
            tone_attributes=self.tone_attributes
            or {
                "formal": 0.3,
                "conversational": 0.8,
                "humorous": 0.4,
            },
            writing_samples=self.writing_samples or [],
            forbidden_phrases=self.forbidden_phrases or [],
            preferred_phrases=self.preferred_phrases or [],
            sentence_structure_preferences=self.sentence_structure_preferences,
            paragraph_style=self.paragraph_style,
            opinion_expression=self.opinion_expression,
            expertise_areas=self.expertise_areas or [],
            created_at=self.created_at,
            updated_at=self.updated_at,
            version=self.version,
        )

    @classmethod
    def from_entity(cls, entity: PersonaProfileEntity) -> "PersonaProfileModel":
        """Create ORM model from domain entity."""
        return cls(
            id=str(entity.id),
            name=entity.name,
            description=entity.description,
            tone_attributes=entity.tone_attributes,
            writing_samples=entity.writing_samples,
            forbidden_phrases=entity.forbidden_phrases,
            preferred_phrases=entity.preferred_phrases,
            sentence_structure_preferences=entity.sentence_structure_preferences,
            paragraph_style=entity.paragraph_style,
            opinion_expression=entity.opinion_expression,
            expertise_areas=entity.expertise_areas,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            version=entity.version,
        )

    def update_from_entity(self, entity: PersonaProfileEntity) -> None:
        """Update ORM model from domain entity."""
        self.name = entity.name
        self.description = entity.description
        self.tone_attributes = entity.tone_attributes
        self.writing_samples = entity.writing_samples
        self.forbidden_phrases = entity.forbidden_phrases
        self.preferred_phrases = entity.preferred_phrases
        self.sentence_structure_preferences = entity.sentence_structure_preferences
        self.paragraph_style = entity.paragraph_style
        self.opinion_expression = entity.opinion_expression
        self.expertise_areas = entity.expertise_areas
        self.updated_at = entity.updated_at
        self.version = entity.version


class QualityRubricModel(Base):
    """SQLAlchemy model for QualityRubric entity."""

    __tablename__ = "quality_rubrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    criteria = Column(JSON, default=list, nullable=False)
    applicable_content_types = Column(JSON, default=lambda: ["carousel"], nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    version = Column(Integer, default=1, nullable=False)

    __table_args__ = (
        Index("idx_quality_rubrics_name", "name"),
        Index("idx_quality_rubrics_is_default", "is_default"),
    )

    def to_entity(self) -> QualityRubricEntity:
        """Convert ORM model to domain entity."""
        from uuid import UUID

        return QualityRubricEntity(
            id=UUID(self.id),
            name=self.name,
            description=self.description,
            criteria=self.criteria,
            applicable_content_types=self.applicable_content_types or ["carousel"],
            is_default=self.is_default,
            created_at=self.created_at,
            updated_at=self.updated_at,
            version=self.version,
        )

    @classmethod
    def from_entity(cls, entity: QualityRubricEntity) -> "QualityRubricModel":
        """Create ORM model from domain entity."""
        return cls(
            id=str(entity.id),
            name=entity.name,
            description=entity.description,
            criteria=entity.criteria,
            applicable_content_types=entity.applicable_content_types,
            is_default=entity.is_default,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            version=entity.version,
        )

    def update_from_entity(self, entity: QualityRubricEntity) -> None:
        """Update ORM model from domain entity."""
        self.name = entity.name
        self.description = entity.description
        self.criteria = entity.criteria
        self.applicable_content_types = entity.applicable_content_types
        self.is_default = entity.is_default
        self.updated_at = entity.updated_at
        self.version = entity.version


class RubricEvaluationScoreModel(Base):
    """SQLAlchemy model for RubricEvaluationScore entity."""

    __tablename__ = "rubric_evaluation_scores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rubric_id = Column(String(36), ForeignKey("quality_rubrics.id"), nullable=False)
    content_id = Column(String(36), nullable=False)
    content_type = Column(String(30), nullable=False)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    scores = Column(JSON, default=dict, nullable=False)
    overall_score = Column(Integer, default=0, nullable=False)
    passed = Column(Boolean, default=False, nullable=False)
    feedback = Column(JSON, default=list, nullable=False)

    __table_args__ = (
        Index("idx_rubric_scores_rubric_id", "rubric_id"),
        Index("idx_rubric_scores_content_id", "content_id"),
        Index("idx_rubric_scores_content_type", "content_type"),
    )

    def to_entity(self) -> RubricEvaluationScore:
        """Convert ORM model to domain entity."""
        from uuid import UUID

        return RubricEvaluationScore(
            rubric_id=UUID(self.rubric_id),
            content_id=UUID(self.content_id),
            content_type=self.content_type,
            evaluated_at=self.evaluated_at,
            scores=self.scores,
            overall_score=float(self.overall_score),
            passed=self.passed,
            feedback=self.feedback,
        )

    @classmethod
    def from_entity(cls, entity: RubricEvaluationScore) -> "RubricEvaluationScoreModel":
        """Create ORM model from domain entity."""
        return cls(
            id=str(uuid.uuid4()),
            rubric_id=str(entity.rubric_id),
            content_id=str(entity.content_id),
            content_type=entity.content_type,
            evaluated_at=entity.evaluated_at,
            scores=entity.scores,
            overall_score=int(entity.overall_score),
            passed=entity.passed,
            feedback=entity.feedback,
        )
