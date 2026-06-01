from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.entities.article_chunk import ArticleChunk
from app.domain.entities.extracted_page import ExtractedPage
from app.infrastructure.db.models.archive import Chunk, Document, DocumentStatus, Page


class SQLAlchemyProcessingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_document(self, document_id: int) -> Document | None:
        stmt = select(Document).where(Document.id == document_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def update_document_status(self, document_id: int, status: DocumentStatus) -> None:
        document = self.get_document(document_id)
        if document is None:
            return

        document.status = status
        self._session.add(document)
        self._session.commit()

    def replace_pages(self, document_id: int, pages: list[ExtractedPage]) -> None:
        self._session.execute(delete(Page).where(Page.document_id == document_id))

        page_rows = [
            Page(
                document_id=document_id,
                page_number=page.page_number,
                ocr_used="tesseract" if page.ocr_used else "native",
                content=page.content,
            )
            for page in pages
        ]
        self._session.add_all(page_rows)
        self._session.commit()

    def replace_chunks(
        self,
        document_id: int,
        chunks: list[ArticleChunk],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Le nombre de chunks et d'embeddings doit etre identique.")

        self._session.execute(delete(Chunk).where(Chunk.document_id == document_id))

        chunk_rows = [
            Chunk(
                document_id=document_id,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=embedding,
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        self._session.add_all(chunk_rows)
        self._session.commit()
