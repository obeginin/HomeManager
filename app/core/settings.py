import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.logger import LoggerConfig
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

    # Proxmox API
    PROX_MAC: str
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
    APP_NAME: str = "app"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = APP_NAME
    LOG_DIR: str = "logs"
    CONSOLE_OUTPUT: bool = True
    USE_JSON: bool = False


    # API & Timezone

    API_PREFIX: str = "/api/v1"
    TIMEZONE: str = "Europe/Moscow"



settings = Settings()
# --- Инициализация логирования ---
logger_config = LoggerConfig(
    log_file=f"{settings.APP_NAME}.log",
    log_level=settings.LOG_LEVEL,
    console_output=settings.CONSOLE_OUTPUT,
    use_json=settings.USE_JSON,
)
logger_config.setup_logger()
logger = logger_config.get_logger(__name__)

# settings.create_dirs() создаются при инициализации init