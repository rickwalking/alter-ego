"""SQLAlchemy model for persisted persona feedback corrections."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, func

from rag_backend.infrastructure.database.config import Base


class PersonaCorrectionModel(Base):
    """Human correction stored for persona feedback learning."""

    __tablename__ = "persona_corrections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    persona_id = Column(
        String(36),
        ForeignKey("persona_profiles.id"),
        nullable=False,
    )
    project_id = Column(String(36), nullable=True)
    original_text = Column(Text, nullable=False, default="")
    corrected_text = Column(Text, nullable=False)
    context = Column(Text, nullable=False, default="")
    correction_type = Column(String(64), nullable=False, default="content")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_persona_corrections_persona_id", "persona_id"),
        Index("idx_persona_corrections_created_at", "created_at"),
    )


__all__ = ["PersonaCorrectionModel"]
