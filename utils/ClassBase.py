from dataclasses import dataclass, field
from typing import Any
import json

@dataclass
class ServiceResponse:
    """Унифицированный формат ответа для обмена между сервисами"""
    status: str = "success"   # success, error, access_denied и т.д.
    msg: str = ""             # Сообщение при успешной операции
    error: str = ""           # Сообщение об ошибке
    data: Any = field(default_factory=dict)  # Любые дополнительные данные

    def to_dict(self) -> dict:
        """Конвертируем в словарь"""
        return {
            "status": self.status,
            "msg": self.msg,
            "error": self.error,
            "data": self.data
        }

    def to_json(self) -> str:
        """Конвертируем в JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
