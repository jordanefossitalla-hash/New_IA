from __future__ import annotations

import logging
from pathlib import Path

import fitz
import pytesseract
from PIL import Image

from app.core.config import settings
from app.domain.entities.extracted_page import ExtractedPage

logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    """Raised when PDF extraction fails."""


class PDFExtractionService:
    def __init__(self) -> None:
        self._ocr_languages = settings.ocr_languages
        self._min_text_chars = settings.extraction_min_text_chars
        self._min_alpha_ratio = settings.extraction_min_alpha_ratio

    def extract_pages(self, pdf_path: str | Path) -> list[ExtractedPage]:
        source = Path(pdf_path)
        if not source.exists():
            logger.error("PDF file not found", extra={"pdf_path": str(source)})
            raise PDFExtractionError(f"PDF introuvable: {source}")

        if source.suffix.lower() != ".pdf":
            logger.error("Unsupported file extension", extra={"pdf_path": str(source)})
            raise PDFExtractionError("Le fichier fourni n'est pas un PDF.")

        try:
            doc = fitz.open(source)
        except Exception as exc:
            logger.exception("Failed to open PDF", extra={"pdf_path": str(source)})
            raise PDFExtractionError("Impossible d'ouvrir le PDF.") from exc

        pages: list[ExtractedPage] = []

        with doc:
            for index in range(doc.page_count):
                page_number = index + 1
                page = doc.load_page(index)
                extracted_text = page.get_text("text").strip()
                ocr_used = False

                if self._is_low_quality(extracted_text):
                    logger.info(
                        "Low quality text detected, using OCR",
                        extra={"pdf_path": str(source), "page_number": page_number},
                    )
                    ocr_used = True
                    try:
                        extracted_text = self._extract_with_ocr(page)
                    except pytesseract.TesseractNotFoundError as exc:
                        logger.exception(
                            "Tesseract executable not found",
                            extra={"pdf_path": str(source), "page_number": page_number},
                        )
                        raise PDFExtractionError(
                            "Tesseract n'est pas installe ou n'est pas accessible dans le PATH."
                        ) from exc
                    except Exception as exc:
                        logger.exception(
                            "OCR extraction failed",
                            extra={"pdf_path": str(source), "page_number": page_number},
                        )
                        raise PDFExtractionError(
                            f"Erreur OCR sur la page {page_number}."
                        ) from exc

                pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        content=extracted_text,
                        ocr_used=ocr_used,
                    )
                )

        logger.info(
            "PDF extraction completed",
            extra={"pdf_path": str(source), "pages": len(pages)},
        )
        return pages

    def _is_low_quality(self, text: str) -> bool:
        if len(text) < self._min_text_chars:
            return True

        alpha_chars = sum(1 for char in text if char.isalpha())
        alpha_ratio = alpha_chars / max(len(text), 1)
        return alpha_ratio < self._min_alpha_ratio

    def _extract_with_ocr(self, page: fitz.Page) -> str:
        pix = page.get_pixmap(dpi=300)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return pytesseract.image_to_string(image, lang=self._ocr_languages).strip()
