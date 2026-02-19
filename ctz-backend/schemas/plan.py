from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any

def _validar_atributos(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("atributos_adicionales debe ser un objeto")
    atributos_normalizados: Dict[str, Any] = {}
    for key, val in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Cada atributo adicional debe tener un nombre válido")
        if isinstance(val, (dict, list)):
            raise ValueError("Los atributos adicionales solo aceptan valores escalares")
        atributos_normalizados[key.strip()] = val
    return atributos_normalizados


class PlanBase(BaseModel):
    nombre: str
    conexiones_incluidas: int
    valor_plan_mensual: float
    valor_conexion_adicional: float
    condiciones: Optional[str]
    activo: bool = True
    atributos_adicionales: Dict[str, Any] = Field(default_factory=dict)

    _normalize_atributos = field_validator("atributos_adicionales", mode="before")(_validar_atributos)

class PlanCreate(PlanBase):
    pass

class PlanUpdate(BaseModel):
    nombre: Optional[str]
    conexiones_incluidas: Optional[int]
    valor_plan_mensual: Optional[float]
    valor_conexion_adicional: Optional[float]
    condiciones: Optional[str]
    activo: Optional[bool]
    atributos_adicionales: Optional[Dict[str, Any]]

    _normalize_atributos = field_validator("atributos_adicionales", mode="before")(_validar_atributos)

class PlanResponse(PlanBase):
    id_plan: int

    class Config:
        from_attributes = True
