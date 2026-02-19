from pydantic import BaseModel
from typing import Optional


class PlanBase(BaseModel):
    nombre: str
    conexiones_incluidas: int
    valor_plan_mensual: float
    valor_conexion_adicional: float
    mensajes_whatsapp: int = 0
    condiciones: Optional[str]
    activo: bool = True


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    nombre: Optional[str]
    conexiones_incluidas: Optional[int]
    valor_plan_mensual: Optional[float]
    valor_conexion_adicional: Optional[float]
    mensajes_whatsapp: Optional[int]
    condiciones: Optional[str]
    activo: Optional[bool]


class PlanResponse(PlanBase):
    id_plan: int

    class Config:
        from_attributes = True
