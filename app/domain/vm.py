# domain/vm.py
from dataclasses import dataclass

@dataclass
class VM:
    vmid: int
    node: str
    status: str

    def is_running(self) -> bool:
        return self.status == "running"