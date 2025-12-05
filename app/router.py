from fastapi import APIRouter, Depends, BackgroundTasks, Query
import requests
import urllib3
import logging
from app.func_proxmox import ProxmoxManager, MikrotikManager
from utils.ClassSettings import settings
logger = logging.getLogger(__name__)


urllib3.disable_warnings()  # отключаем проверку SSL для самоподписанного сертификата


#logger.warning(f"LOGGER OUTSIDE: name={logger.name}, level={logger.level}")
proxmox = ProxmoxManager(logger=logger)
prox = APIRouter(prefix="/prox", tags=["prox"])
prox_ssh = APIRouter(prefix="/prox_ssh", tags=["prox_ssh"])
mikro = APIRouter(prefix="/mikro", tags=["mikro"])
@prox.get("/check")
def check_connection():
    """Возвращает список всех запущенных виртуальных машин на Proxmox."""
    check = proxmox.check_proxmox_connection()
    if check:
        logger.info("Соединение с Proxmox успешно!")
    else:
        logger.info("Не удалось подключиться к Proxmox.")
    return {"status": check}

@prox.get("/running")
def get_running_vms():
    """Возвращает список всех запущенных виртуальных машин на Proxmox."""
    vms = proxmox.get_all_vms()

    # Фильтруем только запущенные VM (status=running)
    running_vms = [vm for vm in vms if vm.get("status") == "running"]
    logger.info(f"Стутас виртуальных машины: {running_vms}")

    return {"running_vms": running_vms}

@prox.post("/start")
def start_all_vms_route():
    """
    Запускает все виртуальные машины на Proxmox.
    Возвращает словарь vmid -> результат (True/False)
    """
    logger.info("Запуск всех ВМ через роут /vms/start")
    results = proxmox.start_all_vms()
    return {"results": results}

@prox.post("/shutdown")
def shutdown_vms(background_tasks: BackgroundTasks):
    """
    Выключает все виртуальные машины на Proxmox.
    Выполняется в фоне, чтобы FastAPI сразу вернул ответ.
    """
    background_tasks.add_task(proxmox.shutdown_all_vms)
    logger.info("Запуск выключения всех виртуальных машин...")
    return {"status": "shutdown of all VMs started"}

@prox.post("/shutdown_pve")
async def shutdown_proxmox(background_tasks: BackgroundTasks, delay: int = Query(0, ge=0, description="Задержка перед выключением VM в минутах")):
    """
    Выключает сам Proxmox сервер после выключения VM.
    Выполняется в фоне.
    delay: int = задержка перед выключением в секундах (по умолчанию 0)
    """
    logger.info(f"Запуск выключения всех VM с задержкой {delay} минут")
    #background_tasks.add_task(proxmox.run_shutdown, delay)
    result = await proxmox.run_shutdown(delay=delay)

    return {"status": "success", "data": result}

@prox_ssh.post("/connect_ssh")
async def connect_ssh(command:str):
    try:
        result = await proxmox.connect_ssh_proxmox(command)
        return {"status": "success", "data": f"{result}"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@mikro.post("/start_prox")
async def connect_ssh():
    try:
        mikro = MikrotikManager(logger=logger)
        result = await mikro.connect_ssh_mikrotik("system script run WakeProxmox")
        return {"status": "success", "data": f"{result}"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
