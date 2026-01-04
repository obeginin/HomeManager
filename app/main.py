from fastapi import FastAPI
import subprocess
#from bot.dispatcher import dp
#from bot.bot import bot
import asyncio
from datetime import datetime
from utils.ClassSettings import logger_config, settings
import logging
from app.router import prox, prox_ssh, mikro



# --- Настройка логирования ---
logger_config.setup_logger()
logger = logging.getLogger(__name__)
logger.info("Запуск приложения")
start_time = datetime.utcnow()

app = FastAPI()



app.include_router(prox)
app.include_router(prox_ssh)
app.include_router(mikro)
# @app.post("/shutdown-proxmox")
# async def shutdown_proxmox():
#     # Запуск в фоне, чтобы не блокировать FastAPI
#     loop = asyncio.get_event_loop()
#     loop.run_in_executor(None, run_shutdown)
#     return {"status": "shutdown started"}

# Запуск Telegram-бота (polling)
# @app.on_event("startup")
# async def start_bot():
#     asyncio.create_task(dp.start_polling(bot))



@app.get("/api/health", tags=["Health"], summary="Проверка состояния сервиса")
async def health_check():
    """Эндпоинт для проверки доступности сервиса и БД."""
    status = "healthy"
    uptime = (datetime.utcnow() - start_time).total_seconds()
    return {
        "status": status,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "uptime_seconds": int(uptime)
    }



