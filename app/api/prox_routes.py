# api/prox_routes.py
from fastapi import APIRouter, BackgroundTasks, Query
from app.use_cases.prox_services import ProxmoxService
from app.infrastructure.prox_api_client import ProxmoxAPIClient
from app.core.settings import settings
from app.core.logger import logger

prox = APIRouter(prefix="/prox", tags=["prox"])
service = ProxmoxService(ProxmoxAPIClient(), logger=logger)

@prox.get("/check", summary="Проверяет соединение с Proxmox")
def check_connection(service: ProxmoxService = Depends(get_proxmox_service)):
    """Проверяет соединение с Proxmox (включен или нет)"""
    response = service.check_connection()
    return response.to_dict()

@prox.get("/running", summary="Запущенные ВМ Proxmox", description= 'Возвращает список всех запущенных виртуальных машин на Proxmox')
def get_running_vms():
    '''Роут для получения всех VM со статусом 'running':'''
    response = service.get_running_vms()
    return response.to_dict()

@prox.post("/start", summary="Запуск всех ВМ Proxmox", description= 'Запускает все Виртуальные машины Proxmox')
def start_all_vms():
    '''Роут запуска всех ВМ:'''
    response = service.start_all_vms()
    return response.to_dict()

@prox.post("/shutdown", summary="Отключение Proxmox", description= 'Сначала запускается отключение всех ВМ, затем самого сервера Proxmox')
async def shutdown_vms(background_tasks: BackgroundTasks, delay: int = Query(0, ge=0)):
    '''Асинхронный роут выключения VM и сервера Proxmox:'''
    background_tasks.add_task(service.shutdown_server, delay)
    return {"status": "shutdown of all VMs started"}

@prox_ssh.post("/connect_ssh", summary="Выполнение команды в консоли Proxmox")
async def connect_ssh(command: str, service: ProxmoxService = Depends(get_proxmox_service)):
    '''Роут для выполнения произвольной команды на Proxmox через SSH:'''
    response = await service.run_ssh_command(command)
    return response.to_dict()
