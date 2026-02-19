from typing import Optional

from pydantic import BaseModel


class CapacitacionPlataformaBase(BaseModel):
    conexiones_desde: int
    conexiones_hasta: Optional[int] = None
    horas_capacitacion: int
    activo: bool = True


class CapacitacionPlataformaCreate(CapacitacionPlataformaBase):
    pass


class CapacitacionPlataformaUpdate(BaseModel):
    conexiones_desde: Optional[int] = None
    conexiones_hasta: Optional[int] = None
    horas_capacitacion: Optional[int] = None
    activo: Optional[bool] = None


class CapacitacionPlataformaResponse(CapacitacionPlataformaBase):
    id_capacitacion_plataforma: int

    class Config:
        from_attributes = True
