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


class PrestacionBase(BaseModel):
    nombre: str
    valor_unitario: Optional[float]= None
    condiciones: Optional[str]
    activo: bool = True
    clp: bool = True
    atributos_adicionales: Dict[str, Any] = Field(default_factory=dict)

    _normalize_atributos = field_validator("atributos_adicionales", mode="before")(_validar_atributos)
    
class PrestacionCreate(PrestacionBase):
    pass

class PrestacionUpdate(BaseModel):
    nombre: Optional[str]
    valor_unitario: Optional[float]
    condiciones: Optional[str]
    activo: Optional[bool]
    clp: Optional[bool]
    atributos_adicionales: Optional[Dict[str, Any]]

    _normalize_atributos = field_validator("atributos_adicionales", mode="before")(_validar_atributos)

class PrestacionResponse(PrestacionBase):
    id_prestacion: int

    class Config:
        from_attributes = True
