from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.domain.repositories.document_repository import DocumentRepository


class DocumentUploadService:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def upload_pdf(
        self,
        journal_name: str,
        publication_date: date,
        file: UploadFile,
    ) -> int:
        if file.content_type != "application/pdf":
            raise ValueError("Seuls les fichiers PDF sont autorises.")

        suffix = Path(file.filename or "").suffix.lower()
        if suffix != ".pdf":
            raise ValueError("Extension de fichier invalide. Un fichier .pdf est requis.")

        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_uuid = str(uuid4())
        destination = upload_dir / f"{file_uuid}.pdf"
        size_limit_bytes = settings.max_upload_size_mb * 1024 * 1024

        bytes_written = 0
        try:
            with destination.open("wb") as output:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > size_limit_bytes:
                        output.close()
                        destination.unlink(missing_ok=True)
                        raise ValueError(
                            f"Fichier trop volumineux. Taille maximale: {settings.max_upload_size_mb} MB."
                        )
                    output.write(chunk)
        finally:
            await file.close()

        document_id = self._repository.create_document(
            journal_name=journal_name,
            publication_date=publication_date,
            file_path=str(destination).replace('\\', '/'),
        )
        return document_id
