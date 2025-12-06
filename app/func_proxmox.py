import requests
import time
import urllib3
import logging
import asyncio
urllib3.disable_warnings()
from utils.ClassSettings import settings
from utils.ClassSSH import AsyncSSHClient
from utils.ClassHTTP import AsyncHttpClient, RequestFormat, ResponseFormat
from utils.ClassBase import ServiceResponse
class ProxmoxManager:
    """CRUD-сервис для работы с Proxmox"""
    def __init__(self, logger: logging.Logger):
        self.logger = logging.getLogger(f"{logger.name}.{self.__class__.__name__}")
        self.headers = {"Authorization": f"PVEAPIToken={settings.PVE_TOKEN}={settings.PVE_SECRET}"}
        #self.logger.info("ProxmoxManager инициализирован")
        self.logger.info("Инициализация ProxmoxManager")


    def check_proxmox_connection(self) -> bool:
        """
        Проверяет соединение с Proxmox API.
        Возвращает True, если соединение успешно, иначе False.
        """
        self.logger.info(f"check_proxmox_connection")
        url = f"{settings.PVE_HOST}/api2/json/cluster/resources?type=vm"
        try:
            resp = requests.get(url, headers=self.headers, verify=False, timeout=5)
            if resp.status_code == 200:
                self.logger.warning(f"200")
                return True
            else:
                self.logger.info(f"Proxmox API returned {resp.status_code}: {resp.text}")
                return False
        except requests.RequestException as e:
            self.logger.exception(f"Error connecting to Proxmox API: {e}")
            return False

    def get_all_vms(self):
        '''Функция для вывода всех запущенных виртуальных машин'''
        url = f"{settings.PVE_HOST}/api2/json/cluster/resources?type=vm"
        resp = requests.get(url, headers=self.headers, verify=False)
        self.logger.info(f"Функция get_all_vms")
        if resp.status_code != 200:
            self.logger.exception(f"Failed to fetch VMs: {resp.status_code}, {resp.text}")
            raise Exception(f"Failed to fetch VMs: {resp.status_code}, {resp.text}")
        return resp.json()["data"]

    def start_all_vms(self):
        """Запускает все ВМ на Proxmox"""
        vms = self.get_all_vms()  # используем уже существующий метод
        results = {}
        for vm in vms:
            vmid = vm["vmid"]
            node = vm["node"]
            results[vmid] = self.start_vm(vmid, node)
        return results

    def start_vm(self, vmid: int, node: str):
        """Запускает конкретную виртуальную машину по vmid и node"""
        self.logger.info(f"Запуск VM {vmid} на ноде {node}")
        try:
            response = requests.post(
                f"{settings.PVE_HOST}/api2/json/nodes/{node}/qemu/{vmid}/status/start",
                headers=self.headers,
                verify=False
            )
            if response.status_code == 200:
                self.logger.info(f"VM {vmid} успешно запущена")
                return True
            else:
                self.logger.warning(f"Не удалось запустить VM {vmid}: {response.status_code}, {response.text}")
                return False
        except requests.RequestException as e:
            self.logger.exception(f"Ошибка при запуске VM {vmid}: {e}")
            return False

    async def wait_for_vms_shutdown(self, timeout=120) -> ServiceResponse:
        """Ждём, пока все VM не выключатся"""
        start = time.time()
        try:
            while True:
                vms = requests.get(
                    f"{settings.PVE_HOST}/api2/json/cluster/resources?type=vm",
                    headers=self.headers,
                    verify=False
                ).json()["data"]

                running = [vm for vm in vms if vm["status"] == "running"]

                if not running:
                    self.logger.info("Все виртуальные машины выключены")
                    return ServiceResponse(status="success", msg=f"Выключено {len(vms)} ВМ")

                if time.time() - start > timeout:
                    self.logger.warning("Таймаут ожидания VM! Некоторые все ещё запущены.")
                    return ServiceResponse(
                        status="error",
                        msg=f"Данные {running} ВМ все ещё запущены"
                    )

                self.logger.info(f"Ожидаем выключения VM... Осталось: {len(running)}")
                await asyncio.sleep(5)
        except Exception as e:
            self.logger.error(f"Ошибка wait_for_vms_shutdown: {e}")
            return ServiceResponse(status="error", error=str(e))

    async def shutdown_all_vms(self) -> ServiceResponse:
        """Выключение виртуальных машин"""
        try:
            async with AsyncHttpClient(url=settings.PVE_HOST, verify_ssl=False, headers=self.headers) as client:

                req_list = RequestFormat(
                    method="GET",
                    endpoint='/api2/json/cluster/resources?type=vm',
                    headers=self.headers,
                    return_type="json"
                )
                resp_list = await client.request_async(request=req_list)

                if resp_list.error:
                    self.logger.error(f"Ошибка получения списка VM: {resp_list.error}")
                    return ServiceResponse(status="error", error=resp_list.error)

                vms = resp_list.data.get("data", [])
                if not vms:
                    self.logger.warning("Список VM пуст, выключать нечего")
                    return ServiceResponse(msg="Нет VM для выключения")

                self.logger.info(f"VM list: {vms}")

                # Формируем таски для выключения
                tasks = []
                for vm in vms:
                    vmid = vm["vmid"]
                    node = vm["node"]

                    req_vm = RequestFormat(
                        method="POST",
                        endpoint=f"/api2/json/nodes/{node}/qemu/{vmid}/status/shutdown",
                        return_type="json"
                    )
                    tasks.append(client.request_async(req_vm))

                # Выполняем параллельно
                shutdown_results = await asyncio.gather(*tasks, return_exceptions=True)

                errors = []
                for vm, result in zip(vms, shutdown_results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Ошибка при выключении VM {vm['vmid']}: {result}")
                        errors.append(str(result))
                    else:
                        self.logger.info(f"VM {vm['vmid']} shutdown result: {result.data}")

                # Ждём полного выключения
                wait_result = await self.wait_for_vms_shutdown()
                if wait_result.status == "success":
                    msg = wait_result.msg
                    return ServiceResponse(msg=msg, data={"shutdown_results": shutdown_results})
                else:
                    return wait_result  # уже ServiceResponse с статусом error

        except Exception as e:
            self.logger.error(f"Глобальная ошибка shutdown_all_vms: {e}")
            return ServiceResponse(status="error", error=str(e))


    def shutdown_pve(self):
        '''Отключение самого Proxmox'''
        self.logger.info(f"Shutting down Proxmox node...")

        # имя ноды — "pve" или "pve1"
        node_name = "pve"
        response = requests.post(
            f"{settings.PVE_HOST}/api2/json/nodes/{node_name}/status/shutdown",
            headers=self.headers,

        )
        self.logger.info(f"Ответ Proxmox: {response.status_code} {response.text}")
        return response.status_code

    async def shutdown_task(self,delay: int):
        """Фоновая задача для выключения VM и сервера"""
        try:
            self.logger.info(f"Запуск выключения всех VM с задержкой {delay} минут")
            result = await self.run_shutdown(delay=delay)
            self.logger.info(f"Завершено выключение Proxmox: {result}")
        except Exception as e:
            self.logger.error(f"Ошибка в shutdown_task: {e}")

    async def run_shutdown(self, delay: int = 0):
        '''Функцяи для последовательного отключения ВМ, а затем Proxmox'''
        try:
            self.logger.info(f"Задержка {delay} минут")
            if delay > 0:
                await asyncio.sleep(delay * 60)  # роут ждёт эту задержку

            self.logger.info(f"Отключаем все ВМ")
            ansver_vms = await self.shutdown_all_vms()

            if ansver_vms.status == "success":
                self.logger.info(f"VM успешно выключены: {ansver_vms.to_dict()}")
                ssh_result = await self.connect_ssh_proxmox(command='shutdown -h now')
                return ServiceResponse(msg="Сервер Proxmox выключен", data={"ssh_result": ssh_result})
            else:
                return ansver_vms
        except Exception as e:
            self.logger.error(f"Ошибка run_shutdown: {e}")
            return ServiceResponse(status="error", error=str(e))



    async def connect_ssh_proxmox(self, command: str):
        '''Выполнение команды через SSH подключение к proxmox'''
        try:
            async with AsyncSSHClient(settings.PVE_HOST_IP, settings.PVE_USER, settings.PVE_PASSWORD, logger=self.logger) as client:
                result = await client.run_command(command)
                self.logger.info(f"{result}")
                return result
        except Exception as e:
            self.logger.error(f"Ошибка SSH подключения: {e}")
            raise


class MikrotikManager:
    '''Класс для работы с mikrotik'''
    def __init__(self, logger: logging.Logger):
        self.logger = logging.getLogger(f"{logger.name}.{self.__class__.__name__}")

    async def connect_ssh_mikrotik(self, command: str):
        '''Выполнение команды через SSH подключение к mikrotik'''
        try:
            async with AsyncSSHClient(
                    host=settings.MIKROTIK_HOST,
                    username=settings.MIKROTIK_USER,
                    password=settings.MIKROTIK_PASSWORD,
                    port=settings.MIKROTIK_PORT,
                    logger=self.logger,
                    ) as client:
                result = await client.run_command(command)
                self.logger.info(f"{result}")
                return result
        except Exception as e:
            self.logger.error(f"Ошибка SSH подключения: {e}")
            raise