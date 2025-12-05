import requests
import time
import urllib3
import logging
import asyncio
urllib3.disable_warnings()
from utils.ClassSettings import settings
from utils.ClassSSH import AsyncSSHClient

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

    def wait_for_vms_shutdown(self, timeout=120):
        """Ждём, пока ВСЕ виртуальные машины не будут выключены"""
        start = time.time()
        self.logger.info(f"wait_for_vms_shutdown")
        while True:
            vms = requests.get(f"{settings.PVE_HOST}/api2/json/cluster/resources?type=vm", headers=self.headers, verify=False ).json()["data"]

            running = [vm for vm in vms if vm["status"] == "running"]

            if not running:
                self.logger.info("Все виртуальные машины выключены")
                return True, len(vms)

            if time.time() - start > timeout:
                self.logger.warning("Таймаут ожидания VM! Некоторые все ещё запущены.")
                return True, running

            self.logger.info(f"Ожидаем выключения VM... Осталось: {len(running)}")
            time.sleep(5)

    def shutdown_all_vms(self):
        '''Отключение виртуальных машин'''
        vms = requests.get(f"{settings.PVE_HOST}/api2/json/cluster/resources?type=vm", headers=self.headers, verify=False).json()["data"]
        self.logger.info(f"shutdown_all_vms")
        for vm in vms:
            vmid = vm["vmid"]
            node = vm["node"]
            self.logger.info(f"Shutting down VM {vmid}")
            requests.post(
                f"{settings.PVE_HOST}/api2/json/nodes/{node}/qemu/{vmid}/status/shutdown",
                headers=self.headers,
                verify=False
            )
        return self.wait_for_vms_shutdown() # проверяем что все ВМ выключены и возвращаем результат


    def shutdown_pve(self):
        '''Отключение самого Proxmox'''
        self.logger.info(f"Shutting down Proxmox node...")

        # имя ноды — "pve" или "pve1"
        node_name = "pve"
        response = requests.post(
            f"{settings.PVE_HOST}/api2/json/nodes/{node_name}/status/shutdown",
            headers=self.headers,
            verify=False
        )
        self.logger.info(f"Ответ Proxmox: {response.status_code} {response.text}")
        return response.status_code

    async def run_shutdown(self, delay: int = 0):
        '''Функцяи для последовательного отключения ВМ, а затем Proxmox'''
        self.logger.info(f"Задержка {delay} минут")
        if delay > 0:
            await asyncio.sleep(delay * 60)  # роут ждёт эту задержку
        self.logger.info(f"Отключаем все ВМ")
        ansver_vms = self.shutdown_all_vms()
        self.logger.info(f"Стутас выключения ВМ: {ansver_vms}")

        return await self.connect_ssh_proxmox(command='shutdown -h now')

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