from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "document_ingestion_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    include=["app.worker.tasks.document_processing"],
)
