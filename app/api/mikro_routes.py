from fastapi import APIRouter
from app.use_cases.mikro_services import MikrotikService
import logging
logger = logging.getLogger(__name__)

mikro = APIRouter(prefix="/mikro", tags=["mikro"])
service = MikrotikService(logger)

@mikro.post("/start_prox", summary="Включение Proxmox через Mikrotik")
async def start_proxmox():
    """Подключаемся по SSH к Mikrotik и запускаем скрипт WakeProxmox"""
    response = await service.wake_proxmox()
    return response.to_dict()

@mikro.post("/run_command", summary="Выполнение команды на Mikrotik")
async def run_command(command: str):
    """Выполнение произвольной команды на Mikrotik"""
    response = await service.run_command(command)
    return response.to_dict()
