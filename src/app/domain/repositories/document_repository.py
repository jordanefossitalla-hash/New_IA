from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date


class DocumentRepository(ABC):
    @abstractmethod
    def create_document(
        self,
        journal_name: str,
        publication_date: date,
        file_path: str,
    ) -> int:
        """Create and persist a document row and return document id."""
