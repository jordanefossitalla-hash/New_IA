from dataclasses import dataclass


@dataclass(slots=True)
class ArticleChunk:
    chunk_index: int
    page_number: int
    content: str
