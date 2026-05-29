"""Persona Agent for voice enforcement and style matching."""

from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.monitoring_langfuse import get_langfuse_runnable_config


class PersonaAgent:
    """Enforces Pedro's writing voice on all AI-generated content."""

    def __init__(self, persona: PersonaProfile, llm: BaseChatModel) -> None:
        self.persona = persona
        self.llm = llm

    async def enforce(self, content: str, context: str = "") -> str:
        """Rewrite content to match the persona's voice."""
        content = sanitize_llm_input(content)
        context = sanitize_llm_input(context)

        style_guide = self._build_style_guide()
        prompt = (
            f"{style_guide}\n\nCONTEXT: {context}\n\nCONTENT TO REWRITE:\n{content}"
        )
        messages: list[BaseMessage] = [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages, get_langfuse_runnable_config())
        return cast(str, response.content)

    async def evaluate_match(self, content: str) -> dict[str, object]:
        """Score how well content matches the persona (0-100)."""
        content = sanitize_llm_input(content)
        style_guide = self._build_style_guide()
        prompt = (
            f"{style_guide}\n\n"
            "Score this content on how well it matches the persona above.\n\n"
            f"CONTENT:\n{content}\n\n"
            "Respond with JSON containing: tone_match, sentence_structure_match, "
            "opinion_strength, originality, human_authenticity, overall, suggestions."
        )
        messages: list[BaseMessage] = [HumanMessage(content=prompt)]
        response = await self.llm.ainvoke(messages, get_langfuse_runnable_config())
        return self._parse_evaluation_response(cast(str, response.content))

    def _parse_evaluation_response(self, response: str) -> dict[str, object]:
        """Parse the evaluation response into a structured dictionary."""
        try:
            data = __import__("json").loads(response)
            return {
                "tone_match": float(data.get("tone_match", 0)),
                "sentence_structure_match": float(
                    data.get("sentence_structure_match", 0)
                ),
                "opinion_strength": float(data.get("opinion_strength", 0)),
                "originality": float(data.get("originality", 0)),
                "human_authenticity": float(data.get("human_authenticity", 0)),
                "overall": float(data.get("overall", 0)),
                "suggestions": data.get("suggestions", []),
            }
        except Exception:
            return {
                "tone_match": 0.0,
                "sentence_structure_match": 0.0,
                "opinion_strength": 0.0,
                "originality": 0.0,
                "human_authenticity": 0.0,
                "overall": 0.0,
                "suggestions": [],
            }

    def _build_style_guide(self) -> str:
        """Build the style guide string from persona attributes."""
        forbidden = "\n".join(
            f"- {phrase}" for phrase in self.persona.forbidden_phrases
        )
        preferred = "\n".join(
            f"- {phrase}" for phrase in self.persona.preferred_phrases
        )
        samples = "\n".join(
            f"- {sample}" for sample in self.persona.writing_samples[:5]
        )
        tone_formal = self.persona.tone_attributes.get("formal", 0.5)
        tone_conv = self.persona.tone_attributes.get("conversational", 0.5)
        tone_hum = self.persona.tone_attributes.get("humorous", 0.5)
        return f"""You are writing as {self.persona.name}.

TONE: formal={tone_formal}, conversational={tone_conv}, humorous={tone_hum}

SENTENCE STRUCTURE: {self.persona.sentence_structure_preferences}

PARAGRAPH STYLE: {self.persona.paragraph_style}

OPINION EXPRESSION: {self.persona.opinion_expression}

FORBIDDEN PHRASES: {forbidden if forbidden else "None"}

PREFERRED PHRASES: {preferred if preferred else "None"}

EXPERTISE AREAS: {", ".join(self.persona.expertise_areas)}

WRITING SAMPLES: {samples if samples else "None"}

INSTRUCTION: Rewrite content to match this voice. Sound authentically human,
with strong opinions, personal anecdotes, zero generic AI-speak.
"""


__all__ = ["PersonaAgent"]
