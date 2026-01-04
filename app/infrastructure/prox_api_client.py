from app.core.settings import settings
from app.core.http import AsyncHttpClient, RequestFormat, ResponseFormat
from app.infrastructure.ssh_client import AsyncSSHClient
import asyncio
import logging
logger = logging.getLogger(__name__)

class ProxmoxAPIClient:
    """Асинхронная обертка над REST API Proxmox с использованием AsyncHttpClient"""

    def __init__(self, logger=None):
        self.host = settings.PVE_HOST
        self.headers = {"Authorization": f"PVEAPIToken={settings.PVE_TOKEN}={settings.PVE_SECRET}"}
        self._client: AsyncHttpClient | None = None
        self.logger = logging.getLogger(self.__class__.__name__)


    async def request_async(self, request: RequestFormat) -> ResponseFormat:
        async with AsyncHttpClient(url=self.host, headers=self.headers, verify_ssl=False) as client:
            return await client.request_async(request)

    async def get_vms(self):
        """Получение списка всех VM"""
        request = RequestFormat(method="GET", endpoint="/api2/json/cluster/resources?type=vm")
        response: ResponseFormat = await self.request_async(request)
        if response.success and isinstance(response.data, dict):
            return response.data.get("data", [])
        else:
            raise Exception(f"[ProxmoxAPIClient.get_vms] Ошибка получения VM: {response.error or response.data}")

    async def start_vm(self, vmid: int, node: str) -> bool:
        """Запуск конкретной VM"""
        request = RequestFormat(method="POST", endpoint=f"/api2/json/nodes/{node}/qemu/{vmid}/status/start")
        response: ResponseFormat = await self.request_async(request)
        if not response.success:
            raise Exception(f"[ProxmoxAPIClient.start_vm] Не удалось запустить VM {vmid} на узле {node}")
        return True

    async def shutdown_vm(self, vmid: int, node: str) -> bool:
        """Выключение конкретной VM"""
        request = RequestFormat(method="POST", endpoint=f"/api2/json/nodes/{node}/qemu/{vmid}/status/shutdown")
        response: ResponseFormat = await self.request_async(request)
        if not response.success:
            raise Exception(f"[ProxmoxAPIClient.shutdown_vm] Не удалось выключить VM {vmid} на узле {node}")
        return True

    async def shutdown_server(self, node_name: str = "pve") -> bool:
        """Выключение Proxmox сервера"""
        request = RequestFormat(method="POST", endpoint=f"/api2/json/nodes/{node_name}/status/shutdown")
        response: ResponseFormat = await self.request_async(request)
        if not response.success:
            raise Exception(f"[ProxmoxAPIClient.shutdown_server] Не удалось выключить сервер {node_name}")
        return True

    async def run_ssh_command(self, command: str):
        """Выполнение произвольной команды на Proxmox через SSH"""
        try:
            async with AsyncSSHClient(
                    host=settings.PVE_HOST_IP,
                    username=settings.PVE_USER,
                    password=settings.PVE_PASSWORD,
                    logger=self.logger
            ) as client:
                result = await client.run_command(command)
                return result  # список строк вывода
        except Exception as e:
            self.logger.error(f"Ошибка SSH подключения к Proxmox: {e}")
            raise