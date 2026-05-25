"""Feedback Learning Loop for continuous persona improvement."""

from dataclasses import dataclass

from rag_backend.agents.constants import DEFAULT_CONFIDENCE
from rag_backend.agents.input_sanitizer import sanitize_llm_input
from rag_backend.infrastructure.external.openai_embeddings import (  # type: ignore[attr-defined]
    OpenAIEmbeddings,
)

# Constants
DRIFT_THRESHOLD = 0.2


@dataclass
class StoredCorrection:
    """A recorded human correction for similarity retrieval."""

    original: str
    corrected: str
    context: str
    correction_type: str


class FeedbackLearningLoop:
    """Learns from human corrections to improve AI outputs over time.

    This component records human corrections and uses them to:
    1. Update persona profiles with new writing samples
    2. Retrieve similar corrections for future generations
    3. Continuously improve voice match quality
    """

    def __init__(
        self,
        session: object,
        embeddings: OpenAIEmbeddings,
    ) -> None:
        """Initialize the feedback learning loop.

        Args:
            session: Async database session
            embeddings: Embedding model for similarity search
        """
        self.session = session
        self.embeddings = embeddings
        self._corrections: dict[str, list[StoredCorrection]] = {}

    async def record_correction(
        self,
        _original: str,
        _corrected: str,
        _context: str,
        _persona_id: object,
        _correction_type: str | None = None,
    ) -> None:
        """Store a human correction for future learning."""
        original = sanitize_llm_input(_original)
        corrected = sanitize_llm_input(_corrected)
        context = sanitize_llm_input(_context)
        persona_id = _persona_id if isinstance(_persona_id, str) else str(_persona_id)
        correction_type = _correction_type or await self.classify_correction(
            original, corrected
        )
        entry = StoredCorrection(
            original=original,
            corrected=corrected,
            context=context,
            correction_type=correction_type,
        )
        self._corrections.setdefault(persona_id, []).append(entry)

    async def get_relevant_examples(
        self, _persona_id: object, _k: int = 3
    ) -> list[str]:
        """Retrieve similar past corrections to improve new outputs."""
        persona_id = _persona_id if isinstance(_persona_id, str) else str(_persona_id)
        entries = self._corrections.get(persona_id, [])
        return [entry.corrected for entry in entries[-_k:]]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        dot_product = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    async def classify_correction(
        self,
        original: str,
        corrected: str,
    ) -> str:
        """Classify the type of correction made.

        Args:
            original: The original text
            corrected: The corrected text

        Returns:
            Classification string (e.g., "tone", "grammar", "clarity", "voice")
        """
        # Simple heuristics
        if len(corrected) < len(original) * 0.5:
            return "conciseness"
        if "!" in corrected and "!" not in original:
            return "tone"
        if corrected.lower().replace(" ", "") != original.lower().replace(" ", ""):
            return "content"
        return "minor_edit"

    async def suggest_improvements(
        self, content: str, _persona_id: object
    ) -> list[str]:
        """Get improvement suggestions based on similar past corrections."""
        persona_id = _persona_id if isinstance(_persona_id, str) else str(_persona_id)
        entries = self._corrections.get(persona_id, [])
        if not entries:
            return []

        content_embedding = await self.embeddings.embed(content)  # type: ignore[attr-defined]
        scored: list[tuple[float, StoredCorrection]] = []
        for entry in entries:
            entry_embedding = await self.embeddings.embed(entry.original)  # type: ignore[attr-defined]
            similarity = self._cosine_similarity(content_embedding, entry_embedding)
            scored.append((similarity, entry))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            f"Consider: {entry.corrected} (was: {entry.original})"
            for _, entry in scored[:3]
        ]

    async def analyze_voice_drift(
        self, _persona_id: object, recent_samples: list[tuple[str, str]]
    ) -> dict[str, object]:
        """Analyze how much the persona voice has drifted from its original."""
        if not recent_samples:
            return {"drift_score": 0.0, "trends": []}

        total_similarity = 0.0
        for original, corrected in recent_samples:
            original_embedding = await self.embeddings.embed(original)  # type: ignore[attr-defined]
            corrected_embedding = await self.embeddings.embed(corrected)  # type: ignore[attr-defined]
            similarity = self._cosine_similarity(
                original_embedding, corrected_embedding
            )
            total_similarity += similarity

        avg_similarity = total_similarity / len(recent_samples)
        drift_score = 1.0 - avg_similarity

        return {
            "drift_score": drift_score,
            "trends": [
                "voice_stable" if drift_score < DRIFT_THRESHOLD else "voice_drifting",
            ],
        }


class CorrectionClassifier:
    """Classifies corrections into categories for better learning.

    Provides structured classification of human corrections to improve
    the feedback learning loop's effectiveness.
    """

    @staticmethod
    def classify(
        original: str,
        corrected: str,
    ) -> dict[str, object]:
        """Classify a correction into categories.

        Args:
            original: Original text
            corrected: Corrected text

        Returns:
            Dictionary with classification results
        """
        classification: dict[str, object] = {
            "correction_type": "tone",
            "severity": "minor",
            "pattern": None,
            "confidence": DEFAULT_CONFIDENCE,
        }

        # Check for tone changes
        if corrected.count("!") > original.count("!"):
            classification["correction_type"] = "tone"
            classification["confidence"] = 0.8

        # Check for grammar fixes
        if original.count("  ") > 0 and "  " not in corrected:
            classification["correction_type"] = "grammar"
            classification["severity"] = "minor"

        # Check for content changes (only if still default classification)
        if (
            original.lower() != corrected.lower()
            and classification["correction_type"] == "tone"
            and classification["confidence"] == DEFAULT_CONFIDENCE
        ):
            classification["correction_type"] = "content"
            classification["confidence"] = 0.7

        return classification


__all__ = ["CorrectionClassifier", "FeedbackLearningLoop"]
