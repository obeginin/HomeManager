import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from utils.ClassLogger import LoggerConfig
from pydantic import Field

# TODO то что требовалось перевел на асинхронный postgres, остальное не обязательно так как используется только при стратре приложения ( не критично)
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram Bot
    TELEGRAM_TOKEN: str
    CHAT_ID: str  # ID чата, куда бот будет отправлять уведомления
    #WEBHOOK_URL: str = None  # если будешь использовать webhook
    API_BASE: str


    #API_URL: str  # например http://127.0.0.1:8000
    #ALLOWED_CHAT_ID: int  # твой Telegram chat_id

    # Proxmox API
    PVE_HOST: str  # например
    PVE_HOST_IP: str
    PVE_USER: str  #
    PVE_PASSWORD: str
    PVE_TOKEN: str  # chatbot
    PVE_SECRET: str  # секрет токена

    # Mikrotik
    MIKROTIK_HOST: str
    MIKROTIK_PORT: str
    MIKROTIK_USER: str
    MIKROTIK_PASSWORD: str

    # Application

    APP_NAME: str = os.getenv("APP_NAME")
    APP_VERSION: str
    ENVIRONMENT: str = os.getenv("ENVIRONMENT")
    DEBUG: bool = False
    # SECRET_KEY: str = Field(..., min_length=16)
    # ALGORITHM: str = "HS256"
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 300


    # Logging & Files

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    LOG_DIR: str = 'logs'

    # API & Timezone

    API_PREFIX: str = "/api/v1"
    TIMEZONE: str = "Europe/Moscow"



settings = Settings()
# --- Инициализация логирования ---
logger_config = LoggerConfig(
    log_dir=settings.LOG_DIR,
    log_file=settings.LOG_FILE,
    log_level=settings.LOG_LEVEL,
    console_output=True,
    use_json=False,
)
# settings.create_dirs() создаются при инициализации init