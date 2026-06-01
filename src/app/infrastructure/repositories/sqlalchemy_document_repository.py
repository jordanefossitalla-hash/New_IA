from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.domain.repositories.document_repository import DocumentRepository
from app.infrastructure.db.models.archive import Document, DocumentStatus


class SQLAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_document(
        self,
        journal_name: str,
        publication_date: date,
        file_path: str,
    ) -> int:
        document = Document(
            journal_name=journal_name,
            publication_date=publication_date,
            file_path=file_path,
            status=DocumentStatus.PENDING,
        )
        self._session.add(document)
        self._session.commit()
        self._session.refresh(document)
        return document.id
