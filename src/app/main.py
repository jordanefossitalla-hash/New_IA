from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging
from app.presentation.api.v1.routers.documents import router as documents_router
from app.presentation.api.v1.routers.health import router as health_router

configure_logging()

app = FastAPI(title=settings.app_name)
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(documents_router, prefix=settings.api_prefix)
