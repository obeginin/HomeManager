from dataclasses import dataclass, field
from typing import Any
import json

class ServiceStatus(str, Enum):
    success = "success"
    error = "error"
    access_denied = "access_denied"
    not_found = "not_found"
    timeout = "timeout"
    warning = "warning"

@dataclass
class ServiceResponse:
    """Унифицированный формат ответа для обмена между сервисами"""
    status: ServiceStatus = ServiceStatus.success   # success, error, access_denied и т.д.
    message: str = ""             # Сообщение при успешной операции
    error: str = None           # Сообщение об ошибке
    data: Any = field(default_factory=dict)  # Любые дополнительные данные

    def to_dict(self) -> dict:
        """Конвертируем в словарь"""
        return {
            "status": self.status,
            "message": self.message,
            "error": self.error,
            "data": self.data
        }

    def to_json(self) -> str:
        """Конвертируем в JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
