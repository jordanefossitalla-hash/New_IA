from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.application.services.document_upload_service import DocumentUploadService
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.sqlalchemy_document_repository import SQLAlchemyDocumentRepository
from app.worker.tasks.document_processing import process_document_task

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


def get_db_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_upload_service(db: Session = Depends(get_db_session)) -> DocumentUploadService:
    repository = SQLAlchemyDocumentRepository(db)
    return DocumentUploadService(repository)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document_pdf(
    journal_name: str = Form(...),
    publication_date: date = Form(...),
    file: UploadFile = File(...),
    service: DocumentUploadService = Depends(get_upload_service),
) -> dict[str, int]:
    try:
        document_id = await service.upload_pdf(
            journal_name=journal_name,
            publication_date=publication_date,
            file=file,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        logger.exception("Database error while uploading document")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur base de donnees lors de l'upload.",
        ) from exc

    try:
        process_document_task.delay(document_id)
    except Exception:
        # Upload is already persisted; keep API successful even if queue is temporarily unavailable.
        logger.exception("Failed to enqueue document processing task", extra={"document_id": document_id})

    return {"document_id": document_id}
