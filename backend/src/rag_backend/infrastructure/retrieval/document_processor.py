"""Document processor for chunking and embedding documents."""

import os

from pypdf import PdfReader

from rag_backend.domain.models import Document, DocumentChunk
from rag_backend.domain.protocols import EmbeddingService


def load_file_content(file_content: bytes, filename: str) -> str:
    """Load and extract text content from a file based on its extension.

    Args:
        file_content: Raw file bytes
        filename: Original filename for extension detection

    Returns:
        Extracted text content

    Raises:
        ValueError: If the file type is unsupported or content cannot be decoded
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        return _load_pdf(file_content)
    elif ext in (".txt", ".md", ".markdown"):
        return file_content.decode("utf-8")
    else:
        return file_content.decode("utf-8")


def _load_pdf(raw_bytes: bytes) -> str:
    """Extract text from all pages of a PDF."""
    import io

    reader = PdfReader(io.BytesIO(raw_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


class RecursiveDocumentProcessor:
    """Document processor using recursive character splitting."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        self._embedding_service = embedding_service
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    async def process(self, document: Document) -> list[DocumentChunk]:
        """Process document into chunks with embeddings."""
        # Split document into chunks
        chunks = self._split_text(document.content)

        # Generate embeddings for all chunks
        dense_embeddings = await self._embedding_service.embed_dense(chunks)
        sparse_embeddings = await self._embedding_service.embed_sparse(chunks)

        # Create DocumentChunk objects
        document_chunks = []
        for i, (chunk_text, dense_emb, sparse_emb) in enumerate(
            zip(chunks, dense_embeddings, sparse_embeddings, strict=False)
        ):
            document_chunks.append(
                DocumentChunk(
                    content=chunk_text,
                    document_id=document.id,
                    index=i,
                    dense_embedding=dense_emb,
                    sparse_embedding=sparse_emb,
                    metadata={
                        "title": document.title,
                        "chunk_index": i,
                        **document.metadata,
                    },
                )
            )

        return document_chunks

    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks using recursive character splitting.

        This is a simplified implementation. For production, consider using
        LangChain's RecursiveCharacterTextSplitter.
        """
        # Define separators in order of preference
        separators = ["\n\n", "\n", ". ", "! ", "? ", " ", ""]

        chunks = []
        remaining = text

        while remaining:
            if len(remaining) <= self._chunk_size:
                chunks.append(remaining.strip())
                break

            # Find the best separator within chunk_size
            chunk = remaining[: self._chunk_size]
            split_pos = self._chunk_size

            for separator in separators:
                pos = chunk.rfind(separator)
                if pos > self._chunk_size * 0.5:  # At least 50% of chunk size
                    split_pos = pos + len(separator)
                    break

            # Add chunk and continue with remaining text
            chunk_text = remaining[:split_pos].strip()
            if chunk_text:
                chunks.append(chunk_text)

            # Move forward with overlap
            remaining = remaining[split_pos - self._chunk_overlap :]

        return chunks

    def estimate_chunks(self, content: str) -> int:
        """Estimate number of chunks for content."""
        token_count = self._embedding_service.count_tokens(content)
        # Rough estimate: ~1 token per 0.75 characters
        char_count = len(content)
        estimated_tokens = max(token_count, char_count // 4)

        # Calculate chunks with overlap
        effective_chunk_size = self._chunk_size - self._chunk_overlap
        if estimated_tokens <= self._chunk_size:
            return 1

        return (estimated_tokens - self._chunk_overlap) // effective_chunk_size + 1
