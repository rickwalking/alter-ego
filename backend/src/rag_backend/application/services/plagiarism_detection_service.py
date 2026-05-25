"""Plagiarism detection via n-gram overlap and embedding similarity (QUAL-001)."""

from __future__ import annotations

import re
from typing import Protocol

from rag_backend.domain.constants.plagiarism import (
    FIELD_MATCHES,
    FIELD_OVERALL_SCORE,
    FIELD_PASSED,
    FIELD_SEVERITY,
    PLAGIARISM_MIN_OVERLAP_RATIO,
    PLAGIARISM_MIN_TEXTS,
    PLAGIARISM_NGRAM_SIZE,
    PLAGIARISM_THRESHOLD_PASS,
    PLAGIARISM_THRESHOLD_WARN,
    SEVERITY_FAIL,
    SEVERITY_PASS,
    SEVERITY_WARN,
)


class EmbeddingServiceProtocol(Protocol):
    async def embed_dense(self, texts: list[str]) -> list[list[float]]: ...


class PlagiarismDetectionService:
    """Detects content similarity against reference sources."""

    def __init__(
        self, embedding_service: EmbeddingServiceProtocol | None = None
    ) -> None:
        self._embedding_service = embedding_service

    async def check(self, content: str, sources: list[str]) -> dict[str, object]:
        """Run plagiarism check and return score with match details."""
        normalized_content = self._normalize(content)
        if not normalized_content.strip():
            return {
                FIELD_OVERALL_SCORE: 100.0,
                FIELD_PASSED: True,
                FIELD_SEVERITY: SEVERITY_PASS,
                FIELD_MATCHES: [],
            }

        matches: list[dict[str, object]] = []
        max_overlap = 0.0

        for idx, source in enumerate(sources):
            normalized_source = self._normalize(source)
            if not normalized_source.strip():
                continue
            overlap = self._ngram_overlap_ratio(normalized_content, normalized_source)
            max_overlap = max(max_overlap, overlap)
            if overlap >= PLAGIARISM_MIN_OVERLAP_RATIO:
                matches.append({
                    "source_index": idx,
                    "overlap_ratio": round(overlap, 4),
                    "method": "ngram",
                })

        embedding_penalty = await self._embedding_similarity_penalty(
            normalized_content, sources
        )
        ngram_score = max(0.0, (1.0 - max_overlap) * 100)
        overall = round(min(ngram_score, embedding_penalty), 2)

        severity = self._severity_for_score(overall)
        return {
            FIELD_OVERALL_SCORE: overall,
            FIELD_PASSED: overall >= PLAGIARISM_THRESHOLD_PASS,
            FIELD_SEVERITY: severity,
            FIELD_MATCHES: matches,
        }

    async def _embedding_similarity_penalty(
        self, content: str, sources: list[str]
    ) -> float:
        if not sources or self._embedding_service is None:
            return 100.0
        texts = [content, *[self._normalize(s) for s in sources if s.strip()]]
        if len(texts) < PLAGIARISM_MIN_TEXTS:
            return 100.0
        embeddings = await self._embedding_service.embed_dense(texts)
        content_vector = embeddings[0]
        max_similarity = 0.0
        for source_vector in embeddings[1:]:
            similarity = self._cosine_similarity(content_vector, source_vector)
            max_similarity = max(max_similarity, similarity)
        return max(0.0, min(100.0, (1.0 - max_similarity) * 100))

    def _severity_for_score(self, score: float) -> str:
        if score >= PLAGIARISM_THRESHOLD_PASS:
            return SEVERITY_PASS
        if score >= PLAGIARISM_THRESHOLD_WARN:
            return SEVERITY_WARN
        return SEVERITY_FAIL

    def _normalize(self, text: str) -> str:
        lowered = text.lower()
        return re.sub(r"\s+", " ", lowered).strip()

    def _ngram_overlap_ratio(self, content: str, source: str) -> float:
        content_ngrams = self._ngrams(content, PLAGIARISM_NGRAM_SIZE)
        source_ngrams = self._ngrams(source, PLAGIARISM_NGRAM_SIZE)
        if not content_ngrams or not source_ngrams:
            return 0.0
        overlap = len(content_ngrams & source_ngrams)
        return overlap / len(content_ngrams)

    def _ngrams(self, text: str, size: int) -> set[str]:
        words = text.split()
        if len(words) < size:
            return set()
        return {" ".join(words[i : i + size]) for i in range(len(words) - size + 1)}

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot_product = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))


__all__ = ["PlagiarismDetectionService"]
