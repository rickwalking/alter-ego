"""Domain models for Persona and Voice Management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict
from uuid import UUID, uuid4

from rag_backend.domain.constants import TONE_CONVERSATIONAL, TONE_FORMAL, TONE_HUMOROUS


class ToneAttributes(TypedDict):
    """Tone attributes for persona voice profile."""
    formal: float
    conversational: float
    humorous: float


@dataclass
class PersonaProfile:
    """Persona profile capturing writing voice and style."""
    id: UUID = field(default_factory=uuid4)
    name: str = "Pedro's Professional Voice"
    description: str = "Professional, opinionated, authentic voice"
    tone_attributes: ToneAttributes = field(default_factory=lambda: {
        "formal": 0.3,
        "conversational": 0.8,
        "humorous": 0.4,
    })
    writing_samples: list[str] = field(default_factory=list)
    forbidden_phrases: list[str] = field(default_factory=list)
    preferred_phrases: list[str] = field(default_factory=list)
    sentence_structure_preferences: str = "Short punchy sentences. Occasional longer ones for rhythm."
    paragraph_style: str = "1-3 sentences per paragraph. White space is key."
    opinion_expression: str = "Strong opinions, loosely held. Never neutral."
    expertise_areas: list[str] = field(default_factory=lambda: ["cybersecurity", "entrepreneurship", "AI"])
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1

    def add_forbidden_phrase(self, phrase: str) -> None:
        """Add a phrase that should never appear."""
        if phrase not in self.forbidden_phrases:
            self.forbidden_phrases.append(phrase)
            self.updated_at = datetime.utcnow()

    def add_preferred_phrase(self, phrase: str) -> None:
        """Add a phrase that characterizes this voice."""
        if phrase not in self.preferred_phrases:
            self.preferred_phrases.append(phrase)
            self.updated_at = datetime.utcnow()

    def add_writing_sample(self, sample: str) -> None:
        """Add a writing sample for voice analysis."""
        self.writing_samples.append(sample)
        # Keep only the best 50 samples
        if len(self.writing_samples) > 50:
            self.writing_samples = self.writing_samples[-50:]
        self.updated_at = datetime.utcnow()
