from __future__ import annotations

import logging
import re

from app.domain.entities.article_chunk import ArticleChunk
from app.domain.entities.extracted_page import ExtractedPage

logger = logging.getLogger(__name__)
_TOKEN_PATTERN = re.compile(r"\S+")


class ChunkingError(Exception):
    """Raised when chunking input is invalid or cannot be processed."""


class TextChunkingService:
    def __init__(self, chunk_size: int = 500, overlap: int = 100) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size doit etre strictement positif.")
        if overlap < 0:
            raise ValueError("overlap ne peut pas etre negatif.")
        if overlap >= chunk_size:
            raise ValueError("overlap doit etre inferieur a chunk_size.")

        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk_pages(self, pages: list[ExtractedPage]) -> list[ArticleChunk]:
        if not pages:
            logger.info("No pages provided for chunking")
            return []

        chunks: list[ArticleChunk] = []
        chunk_index = 0

        for page in pages:
            if page.page_number <= 0:
                logger.error("Invalid page number", extra={"page_number": page.page_number})
                raise ChunkingError("page_number doit etre superieur a 0.")

            page_chunks = self._chunk_single_page(page, start_chunk_index=chunk_index)
            chunks.extend(page_chunks)
            chunk_index += len(page_chunks)

        logger.info("Chunking completed", extra={"pages": len(pages), "chunks": len(chunks)})
        return chunks

    def _chunk_single_page(self, page: ExtractedPage, start_chunk_index: int) -> list[ArticleChunk]:
        content = page.content.strip()
        if not content:
            return []

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", content) if p.strip()]
        if not paragraphs:
            return []

        tokens: list[str] = []
        paragraph_end_indices: set[int] = set()

        for paragraph in paragraphs:
            paragraph_tokens = self._tokenize(paragraph)
            if not paragraph_tokens:
                continue
            tokens.extend(paragraph_tokens)
            paragraph_end_indices.add(len(tokens))

        if not tokens:
            return []

        chunked: list[ArticleChunk] = []
        start = 0
        local_index = 0

        while start < len(tokens):
            tentative_end = min(start + self._chunk_size, len(tokens))
            end = self._prefer_paragraph_boundary(start, tentative_end, paragraph_end_indices)
            if end <= start:
                end = tentative_end

            chunk_tokens = tokens[start:end]
            if not chunk_tokens:
                break

            chunked.append(
                ArticleChunk(
                    chunk_index=start_chunk_index + local_index,
                    page_number=page.page_number,
                    content=" ".join(chunk_tokens),
                )
            )
            local_index += 1

            if end >= len(tokens):
                break

            next_start = max(end - self._overlap, 0)
            if next_start <= start:
                next_start = start + 1
            start = next_start

        return chunked

    def _prefer_paragraph_boundary(
        self,
        start: int,
        tentative_end: int,
        paragraph_end_indices: set[int],
    ) -> int:
        if tentative_end in paragraph_end_indices:
            return tentative_end

        # Try to keep article structure by cutting on a nearby paragraph boundary.
        min_end = max(start + int(self._chunk_size * 0.7), start + 1)
        candidates = [idx for idx in paragraph_end_indices if min_end <= idx <= tentative_end]
        if not candidates:
            return tentative_end
        return max(candidates)

    def _tokenize(self, text: str) -> list[str]:
        return _TOKEN_PATTERN.findall(text)
