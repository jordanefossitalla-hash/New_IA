from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Document Ingestion Platform", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    upload_dir: str = Field(default="storage/uploads", alias="UPLOAD_DIR")
    max_upload_size_mb: int = Field(default=20, alias="MAX_UPLOAD_SIZE_MB")
    ocr_languages: str = Field(default="fra+eng", alias="OCR_LANGUAGES")
    extraction_min_text_chars: int = Field(default=30, alias="EXTRACTION_MIN_TEXT_CHARS")
    extraction_min_alpha_ratio: float = Field(default=0.5, alias="EXTRACTION_MIN_ALPHA_RATIO")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    openai_embedding_batch_size: int = Field(default=50, alias="OPENAI_EMBEDDING_BATCH_SIZE")
    openai_embedding_max_retries: int = Field(default=5, alias="OPENAI_EMBEDDING_MAX_RETRIES")
    openai_embedding_retry_base_delay: float = Field(
        default=1.0,
        alias="OPENAI_EMBEDDING_RETRY_BASE_DELAY",
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    celery_broker_url: str = Field(alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(alias="CELERY_RESULT_BACKEND")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
