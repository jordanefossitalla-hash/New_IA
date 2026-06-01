from dataclasses import dataclass


@dataclass(slots=True)
class ExtractedPage:
    page_number: int
    content: str
    ocr_used: bool
