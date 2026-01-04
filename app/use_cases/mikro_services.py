from app.infrastructure.ssh_client import AsyncSSHClient
from app.core.base import ServiceResponse
from app.core.settings import settings
import logging


class MikrotikService:
    """Сервис для работы с Mikrotik через SSH"""

    def __init__(self, logger: logging.Logger):
        self.logger = logging.getLogger(f"{logger.name}.{self.__class__.__name__}")

    async def run_command(self, command: str) -> ServiceResponse:
        """Выполнение любой команды на Mikrotik"""
        try:
            async with AsyncSSHClient(
                    host=settings.MIKROTIK_HOST,
                    username=settings.MIKROTIK_USER,
                    password=settings.MIKROTIK_PASSWORD,
                    port=int(settings.MIKROTIK_PORT),
                    logger=self.logger
            ) as client:
                result = await client.run_command(command)
            return ServiceResponse(msg="Команда выполнена успешно", data={"result": result})
        except Exception as e:
            self.logger.error(f"Ошибка выполнения команды на Mikrotik: {e}")
            return ServiceResponse(status="error", error=str(e))

    async def wake_proxmox(self) -> ServiceResponse:
        """Запуск сервера Proxmox через Mikrotik"""
        return await self.run_command("system script run WakeProxmox")
