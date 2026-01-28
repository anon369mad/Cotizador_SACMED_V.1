from pydantic import BaseModel
from typing import Optional

class IvaBase(BaseModel):
    nombre: str
    porcentaje: float
    activo: Optional[bool] = True

class IvaCreate(IvaBase):
    pass

class IvaUpdate(BaseModel):
    nombre: Optional[str]
    porcentaje: Optional[float]
    activo: Optional[bool]

class IvaResponse(IvaBase):
    id_iva: int

    class Config:
        from_attributes = True
