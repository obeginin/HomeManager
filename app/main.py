from fastapi import FastAPI
import subprocess
import asyncio
from datetime import datetime

import logging
from app.api.prox_routes import prox
from app.api.mikro_routes import mikro
from app.core.settings import settings
from app.core.response import ServiceStatus

logging.getLogger("asyncssh").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

logger.info("Запуск приложения")
start_time = datetime.utcnow()

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.include_router(prox)
app.include_router(mikro)

@app.get("/api/health", tags=["Health"], summary="Проверка состояния сервиса")
async def health_check():
    """Эндпоинт для проверки доступности сервиса и БД."""
    status = ServiceStatus.success
    uptime = (datetime.utcnow() - start_time).total_seconds()
    return {
        "status": status,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "uptime_seconds": int(uptime)
    }



