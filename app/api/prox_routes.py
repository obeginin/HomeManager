# api/prox_routes.py
import asyncio
from fastapi import APIRouter, BackgroundTasks, Query, Depends
from app.use_cases.prox_services import ProxmoxService
from app.infrastructure.prox_api_client import ProxmoxAPIClient
from app.core.response import ServiceResponse, ServiceStatus
import logging
logger = logging.getLogger(__name__)

def get_proxmox_service() -> ProxmoxService:
    """Dependency для FastAPI. Возвращает экземпляр ProxmoxService"""
    api_client = ProxmoxAPIClient(logger=logger)
    return ProxmoxService(api_client=api_client, logger=logger)

prox = APIRouter(prefix="/prox", tags=["prox"])

@prox.post("/start", summary="Включение Proxmox по WOL")
async def start_proxmox(service: ProxmoxService = Depends(get_proxmox_service)):
    """Отправляет WOL-пакет для включения Proxmox"""
    response = await service.send_wol()
    return response.to_dict()

@prox.get("/check", summary="Проверяет соединение с Proxmox")
async def check_connection(service: ProxmoxService = Depends(get_proxmox_service)):
    """Проверяет соединение с Proxmox (включен или нет)"""
    response = await service.check_connection()
    return response.to_dict()

@prox.get("/running", summary="Запущенные ВМ Proxmox", description= 'Возвращает список всех запущенных виртуальных машин на Proxmox')
async def get_running_vms(service: ProxmoxService = Depends(get_proxmox_service)):
    '''Роут для получения всех VM со статусом 'running':'''
    response = await service.get_running_vms()
    return response.to_dict()

@prox.post("/start_all_vms", summary="Запуск всех ВМ Proxmox", description= 'Запускает все Виртуальные машины Proxmox')
async def start_all_vms(service: ProxmoxService = Depends(get_proxmox_service)):
    '''Роут запуска всех ВМ:'''
    response = await service.start_all_vms()
    return response.to_dict()


@prox.post("/shutdown", summary="Отключение Proxmox")
async def shutdown_vms(delay: int = Query(0, ge=0), service: ProxmoxService = Depends(get_proxmox_service)):
    """Инициация shutdown всех VM и сервера Proxmox"""
    asyncio.create_task(service.shutdown_server(delay))
    return ServiceResponse(status=ServiceStatus.success,message=f"Отключение Proxmox и  всех VM через {delay} минут").to_dict()

@prox.post("/connect_ssh", summary="Выполнение команды в консоли Proxmox")
async def connect_ssh(command: str, service: ProxmoxService = Depends(get_proxmox_service)):
    '''Роут для выполнения произвольной команды на Proxmox через SSH:'''
    response = await service.run_ssh_command(command)
    return response.to_dict()
