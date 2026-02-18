from pydantic import BaseModel
from typing import Optional

class IvaBase(BaseModel):
    porcentaje: float
    activo: Optional[bool] = True

class IvaCreate(IvaBase):
    pass

class IvaUpdate(BaseModel):
    porcentaje: Optional[float]
    activo: Optional[bool]

class IvaResponse(IvaBase):
    id_iva: int

    class Config:
        from_attributes = True
