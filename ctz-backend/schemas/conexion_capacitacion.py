from typing import Optional
from pydantic import BaseModel


class ConexionCapacitacionBase(BaseModel):
    conexiones: int
    horas_capacitacion: int
    activo: bool = True


class ConexionCapacitacionCreate(ConexionCapacitacionBase):
    pass


class ConexionCapacitacionUpdate(BaseModel):
    conexiones: Optional[int] = None
    horas_capacitacion: Optional[int] = None
    activo: Optional[bool] = None


class ConexionCapacitacionResponse(ConexionCapacitacionBase):
    id_conexion_capacitacion: int

    class Config:
        from_attributes = True
