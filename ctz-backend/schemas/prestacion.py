from pydantic import BaseModel
from typing import Optional

class PrestacionBase(BaseModel):
    nombre: str
    valor_unitario: Optional[float]= None
    condiciones: Optional[str]
    activo: bool = True
    clp: bool = True
    
class PrestacionCreate(PrestacionBase):
    pass

class PrestacionUpdate(BaseModel):
    nombre: Optional[str]
    valor_unitario: Optional[float]
    condiciones: Optional[str]
    activo: Optional[bool]
    clp: bool = True

class PrestacionResponse(PrestacionBase):
    id_prestacion: int

    class Config:
        from_attributes = True
