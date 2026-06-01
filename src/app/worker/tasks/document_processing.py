from __future__ import annotations

import asyncio
import logging

from celery import Task
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.openai_embedding_service import EmbeddingServiceError, OpenAIEmbeddingService
from app.application.services.pdf_extraction_service import PDFExtractionError, PDFExtractionService
from app.application.services.text_chunking_service import ChunkingError, TextChunkingService
from app.infrastructure.db.models.archive import DocumentStatus
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.sqlalchemy_processing_repository import SQLAlchemyProcessingRepository
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="document.process", max_retries=5)
def process_document_task(self: Task, document_id: int) -> dict[str, int | str]:
    logger.info("Document processing started", extra={"document_id": document_id})

    with SessionLocal() as session:
        repository = SQLAlchemyProcessingRepository(session)
        document = repository.get_document(document_id)
        if document is None:
            logger.error("Document not found for processing", extra={"document_id": document_id})
            return {"document_id": document_id, "status": "not_found"}

        try:
            logger.info("Step 1/8 - Update status to processing", extra={"document_id": document_id})
            repository.update_document_status(document_id, DocumentStatus.PROCESSING)

            logger.info("Step 2/8 + 3/8 - Extract text with OCR fallback", extra={"document_id": document_id})
            extraction_service = PDFExtractionService()
            pages = extraction_service.extract_pages(document.file_path)

            logger.info("Step 4/8 - Store pages", extra={"document_id": document_id, "pages": len(pages)})
            repository.replace_pages(document_id=document_id, pages=pages)

            logger.info("Step 5/8 - Chunk content", extra={"document_id": document_id})
            chunking_service = TextChunkingService(chunk_size=500, overlap=100)
            chunks = chunking_service.chunk_pages(pages)

            logger.info("Step 6/8 - Generate embeddings", extra={"document_id": document_id, "chunks": len(chunks)})
            embedding_service = OpenAIEmbeddingService()
            embeddings = asyncio.run(embedding_service.embed_texts([chunk.content for chunk in chunks]))

            logger.info("Step 7/8 - Store chunks in PostgreSQL", extra={"document_id": document_id})
            repository.replace_chunks(document_id=document_id, chunks=chunks, embeddings=embeddings)

            logger.info("Step 8/8 - Update status to completed", extra={"document_id": document_id})
            repository.update_document_status(document_id, DocumentStatus.COMPLETED)
            logger.info(
                "Document processing completed",
                extra={"document_id": document_id, "pages": len(pages), "chunks": len(chunks)},
            )
            return {
                "document_id": document_id,
                "status": DocumentStatus.COMPLETED.value,
                "pages": len(pages),
                "chunks": len(chunks),
            }
        except (PDFExtractionError, ChunkingError, EmbeddingServiceError, SQLAlchemyError, ValueError) as exc:
            attempt = self.request.retries + 1
            max_retries = self.max_retries or 5
            delay_seconds = min(30 * (2 ** self.request.retries), 300)

            logger.warning(
                "Document processing failed, retry scheduled",
                extra={
                    "document_id": document_id,
                    "attempt": attempt,
                    "max_retries": max_retries,
                    "delay_seconds": delay_seconds,
                    "error": str(exc),
                },
            )

            if self.request.retries < max_retries:
                raise self.retry(exc=exc, countdown=delay_seconds)

            repository.update_document_status(document_id, DocumentStatus.FAILED)
            logger.exception(
                "Document processing permanently failed",
                extra={"document_id": document_id, "error": str(exc)},
            )
            raise
        except Exception as exc:
            repository.update_document_status(document_id, DocumentStatus.FAILED)
            logger.exception(
                "Unexpected document processing error",
                extra={"document_id": document_id, "error": str(exc)},
            )
            raise
