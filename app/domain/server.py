# domain/server.py
from dataclasses import dataclass

@dataclass
class ProxmoxServer:
    host: str
    name: str