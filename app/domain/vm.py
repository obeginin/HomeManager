# domain/vm.py
from pydantic import BaseModel


class VM(BaseModel):
    vmid: int
    name: str
    status: str

    class Config:
        extra = "ignore"

    def to_dict(self):
        return {"vmid": self.vmid, "name": self.name, "status": self.status}