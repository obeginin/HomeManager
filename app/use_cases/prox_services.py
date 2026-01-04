# application/prox_services.py
import asyncio
from wakeonlan import send_magic_packet
import time
from app.domain.vm import VM
from app.infrastructure.prox_api_client import ProxmoxAPIClient
from app.infrastructure.ssh_client import AsyncSSHClient
from app.core.response import ServiceResponse, ServiceStatus
from app.core.settings import settings
import logging
logger = logging.getLogger(__name__)


def service_handler(default_msg: str = ""):
    """Декоратор для унифицированной обработки ошибок и ServiceResponse"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                result = await func(self, *args, **kwargs)
                # Если метод вернул ServiceResponse, возвращаем его
                if isinstance(result, ServiceResponse):
                    return result
                # Иначе считаем, что операция успешна и возвращаем стандартный ответ
                return ServiceResponse(status=ServiceStatus.success, message=default_msg or "Операция выполнена", data=result)
            except Exception as e:
                self.logger.error(f"Ошибка {func.__name__}: {e}")
                return ServiceResponse(status=ServiceStatus.error, message=default_msg or "Ошибка выполнения операции", error=str(e))
        return wrapper
    return decorator

class ProxmoxService:
    def __init__(self, api_client: ProxmoxAPIClient, logger: logging.Logger):
        self.client = api_client
        self.logger = logging.getLogger(self.__class__.__name__)

    async def send_wol(self) -> ServiceResponse:
        """Отправка WOL-пакета через библиотеку wakeonlan"""
        try:
            send_magic_packet(settings.PROX_MAC, ip_address=settings.PVE_HOST_IP)
            self.logger.info(f"WOL-пакет отправлен {settings.PROX_MAC}")
            return ServiceResponse(status=ServiceStatus.success, message=f"WOL-пакет отправлен" )
        except Exception as e:
            logger.error(f"Ошибка отправки WOL-пакета: {e}")
            return ServiceResponse(status=ServiceStatus.error, message="Ошибка отправки WOL-пакета", error=str(e))


    async def _call_client(self, func, *args, msg: str = "", **kwargs) -> ServiceResponse:
        '''приватный метод, который делает try/except и возвращает ServiceResponse'''
        try:
            result = await func(*args, **kwargs)
            return ServiceResponse(status=ServiceStatus.success, message=msg, data=result)
        except Exception as e:
            self.logger.error(f"Ошибка {func.__name__}: {e}")
            return ServiceResponse(status=ServiceStatus.error, message=msg or "Ошибка", error=str(e))

    async def check_connection(self) -> ServiceResponse:
        """Проверка доступности Proxmox API"""
        try:
            _ = await self.client.get_vms()  # если запрос успешный — соединение ок
            return ServiceResponse(status=ServiceStatus.success, message="Соединение с Proxmox успешно", data={"status": 200})
        except Exception as e:
            self.logger.error(f"Ошибка соединения с Proxmox: {e}")
            return ServiceResponse(status=ServiceStatus.error, message="Не удалось подключиться к Proxmox", error=str(e))

    async def get_running_vms(self):
        """Возвращает список запущенных VM"""
        try:
            vms_data = await self.client.get_vms()
            vms = [VM(**vm) for vm in vms_data]
            running = [vm.to_dict() for vm in vms if vm.status == "running"]
            return ServiceResponse(status=ServiceStatus.success, message="Список запущенных VM", data={"running_vms": running})
        except Exception as e:
            self.logger.error(f"Ошибка получения списка VM: {e}")
            return ServiceResponse(status=ServiceStatus.error, message="Ошибка получения списка VM", error=str(e))

    async def start_vm(self, vmid: int, node: str) -> ServiceResponse:
        """Запуск одной виртуальной машины"""
        try:
            result = await self.client.start_vm(vmid, node)
            return ServiceResponse(status=ServiceStatus.success, message=f"VM {vmid} запущена", data={"result": result})
        except Exception as e:
            self.logger.error(f"Ошибка запуска VM {vmid}: {e}")
            return ServiceResponse(status=ServiceStatus.error, message=f"Ошибка запуска VM {vmid}", error=str(e))

    async def start_all_vms(self):
        """Запуск всех виртуальных машин"""
        try:
            vms_data = await self.client.get_vms()
            results = {}
            for vm in vms_data:
                results[vm["vmid"]] = await self.client.start_vm(vm["vmid"], vm["node"])
            return ServiceResponse(status=ServiceStatus.success, message="Запуск всех VM завершен", data={"results": results})
        except Exception as e:
            self.logger.error(f"Ошибка запуска всех VM: {e}")
            return ServiceResponse(status=ServiceStatus.error, message="Ошибка запуска всех VM", error=str(e))

    async def wait_for_vms_shutdown(self, timeout: int = 120) -> ServiceResponse:
        """Ждём, пока все VM не выключатся"""
        start = time.time()
        try:
            while True:
                vms_data = await self.client.get_vms()
                running = [vm for vm in vms_data if vm.get("status") == "running"]

                if not running:
                    self.logger.info("Все виртуальные машины выключены")
                    return ServiceResponse(status=ServiceStatus.success, message=f"Выключено {len(vms_data)} ВМ")

                if time.time() - start > timeout:
                    self.logger.warning("Таймаут ожидания VM! Некоторые все ещё запущены")
                    return ServiceResponse(status=ServiceStatus.error, message=f"Таймаут ожидания VM! Некоторые все ещё запущены", error=f"Данные {running} ВМ все ещё запущены")

                self.logger.info(f"Ожидаем выключения VM... Осталось: {len(running)}")
                await asyncio.sleep(5)
        except Exception as e:
            self.logger.error(f"Ошибка wait_for_vms_shutdown: {e}")
            return ServiceResponse(status=ServiceStatus.error, message="Ошибка wait_for_vms_shutdown", error=str(e))

    async def shutdown_all_vms(self) -> ServiceResponse:
        """Выключаем все VM и ждём завершения"""
        try:
            vms_data = await self.client.get_vms()
            tasks = [self.client.shutdown_vm(vm["vmid"], vm["node"]) for vm in vms_data]
            await asyncio.gather(*tasks)

            # Ждём полного выключения VM
            wait_result = await self.wait_for_vms_shutdown()
            return wait_result
        except Exception as e:
            self.logger.error(f"Ошибка shutdown_all_vms: {e}")
            return ServiceResponse(status=ServiceStatus.error, message="Ошибка shutdown_all_vms:", error=str(e))

    async def shutdown_server(self, delay: int = 0) -> None:
        """Выключение всех VM с задержкой и самого сервера Proxmox"""
        try:
            if delay > 0:
                self.logger.info(f"Задержка перед shutdown {delay} минут")
                await asyncio.sleep(delay * 60)

            # 1. Выключаем все VM
            vms_result = await self.shutdown_all_vms()
            if vms_result.status != ServiceStatus.success:
                return vms_result

            # 2. Выключаем сервер через SSH
            async with AsyncSSHClient(
                settings.PVE_HOST_IP,
                settings.PVE_USER,
                settings.PVE_PASSWORD,
                self.logger
            ) as client:
                ssh_result = await client.run_command("shutdown -h now")

            self.logger.info("Shutdown сервера инициирован")
        except Exception as e:
            self.logger.error(f"Ошибка при shutdown Proxmox: {e}")

    async def run_ssh_command(self, command: str) -> ServiceResponse:
        """Выполнение команды на сервере через SSH"""
        try:
            async with AsyncSSHClient(
                settings.PVE_HOST_IP,
                settings.PVE_USER,
                settings.PVE_PASSWORD,
                self.logger
            ) as client:
                result = await client.run_command(command)
            return ServiceResponse(status=ServiceStatus.success, message="Команда выполнена успешно", data={"result": result})
        except Exception as e:
            self.logger.error(f"Ошибка SSH подключения к Proxmox: {e}")
            return ServiceResponse(status=ServiceStatus.error, message="Ошибка SSH подключения к Proxmox", error=str(e))