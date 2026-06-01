from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(Exception):
    """Raised when embeddings generation fails."""


class OpenAIEmbeddingService:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise EmbeddingServiceError("OPENAI_API_KEY est requis pour utiliser le service d'embeddings.")

        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_embedding_model
        self._batch_size = settings.openai_embedding_batch_size
        self._max_retries = settings.openai_embedding_max_retries
        self._base_delay = settings.openai_embedding_retry_base_delay

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        cleaned_texts = [text.strip() for text in texts if text and text.strip()]
        if not cleaned_texts:
            return []

        vectors: list[list[float]] = []

        for batch_index, batch in enumerate(self._chunk_iterable(cleaned_texts, self._batch_size)):
            logger.info(
                "Embedding batch started",
                extra={
                    "batch_index": batch_index,
                    "batch_size": len(batch),
                    "model": self._model,
                },
            )
            response = await self._request_with_retry(batch=batch, batch_index=batch_index)
            vectors.extend([item.embedding for item in response.data])

        logger.info("Embeddings generated", extra={"texts": len(cleaned_texts), "vectors": len(vectors)})
        return vectors

    async def _request_with_retry(self, batch: list[str], batch_index: int):
        attempt = 0
        while True:
            try:
                return await self._client.embeddings.create(
                    model=self._model,
                    input=batch,
                )
            except RateLimitError as exc:
                attempt += 1
                if attempt > self._max_retries:
                    logger.exception(
                        "Max retries exceeded after rate limit",
                        extra={"batch_index": batch_index, "attempt": attempt},
                    )
                    raise EmbeddingServiceError("Rate limit OpenAI depasse apres plusieurs tentatives.") from exc

                delay = self._extract_retry_delay(exc, attempt)
                logger.warning(
                    "Rate limit encountered, retrying",
                    extra={"batch_index": batch_index, "attempt": attempt, "delay_seconds": delay},
                )
                await asyncio.sleep(delay)
            except (APITimeoutError, APIConnectionError) as exc:
                attempt += 1
                if attempt > self._max_retries:
                    logger.exception(
                        "Max retries exceeded after network/timeout error",
                        extra={"batch_index": batch_index, "attempt": attempt},
                    )
                    raise EmbeddingServiceError("Erreur reseau OpenAI persistante.") from exc

                delay = min(self._base_delay * (2 ** (attempt - 1)), 30.0)
                logger.warning(
                    "Transient connection error, retrying",
                    extra={"batch_index": batch_index, "attempt": attempt, "delay_seconds": delay},
                )
                await asyncio.sleep(delay)
            except APIStatusError as exc:
                status_code = exc.status_code
                if status_code >= 500:
                    attempt += 1
                    if attempt > self._max_retries:
                        logger.exception(
                            "Max retries exceeded after server error",
                            extra={"batch_index": batch_index, "attempt": attempt, "status_code": status_code},
                        )
                        raise EmbeddingServiceError("Erreur serveur OpenAI persistante.") from exc

                    delay = min(self._base_delay * (2 ** (attempt - 1)), 30.0)
                    logger.warning(
                        "OpenAI server error, retrying",
                        extra={
                            "batch_index": batch_index,
                            "attempt": attempt,
                            "status_code": status_code,
                            "delay_seconds": delay,
                        },
                    )
                    await asyncio.sleep(delay)
                    continue

                logger.exception(
                    "OpenAI API status error",
                    extra={"batch_index": batch_index, "status_code": status_code},
                )
                raise EmbeddingServiceError(f"Erreur API OpenAI ({status_code}).") from exc
            except Exception as exc:
                logger.exception("Unexpected error while generating embeddings", extra={"batch_index": batch_index})
                raise EmbeddingServiceError("Erreur inattendue pendant la generation des embeddings.") from exc

    def _extract_retry_delay(self, error: RateLimitError, attempt: int) -> float:
        retry_after_value = None

        response = getattr(error, "response", None)
        if response is not None:
            headers = getattr(response, "headers", None)
            if headers:
                retry_after_value = headers.get("retry-after")

        if retry_after_value is not None:
            try:
                retry_after_seconds = float(retry_after_value)
                if retry_after_seconds > 0:
                    return min(retry_after_seconds, 60.0)
            except ValueError:
                pass

        return min(self._base_delay * (2 ** (attempt - 1)), 60.0)

    @staticmethod
    def _chunk_iterable(items: list[str], size: int) -> Iterable[list[str]]:
        for index in range(0, len(items), size):
            yield items[index : index + size]
