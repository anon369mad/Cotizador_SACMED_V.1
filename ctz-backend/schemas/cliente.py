from pydantic import BaseModel
from typing import Optional

class ClienteBase(BaseModel):
    razon_social: str
    rut: str

class ClienteCreate(ClienteBase):
    pass

class ClienteResponse(ClienteBase):
    id_cliente: int

    class Config:
        from_attributes = True

class ClienteUpdate(BaseModel):
    razon_social: Optional[str] = None
    rut: Optional[str] = None
