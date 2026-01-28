from pydantic import BaseModel
from typing import Optional
from datetime import date
# un schema es una representación estructurada de los datos que se utilizan para validar y serializar la información que se intercambia entre el cliente y el servidor en una API.
#mas simplemente, los schemas definen cómo deben lucir los datos que se envían y reciben, asegurando que cumplan con ciertos formatos y tipos antes de ser procesados o almacenados.
class CotizacionBase(BaseModel):
    tipo: str  # PERIODO | UNICA
    id_cliente: int
    id_usuario: int
    id_iva: int
    meses: Optional[int]
    conexiones: Optional[int]
    condiciones_adicionales: Optional[str]

class CotizacionCreate(CotizacionBase):
    pass

class CotizacionUpdate(BaseModel):
    estado: Optional[str]
    condiciones_adicionales: Optional[str]

class CotizacionResponse(CotizacionBase):
    id_cotizacion: int
    subtotal: float
    descuento_total: float
    iva_monto: float
    total: float
    estado: str
    fecha_emision: date
    fecha_vencimiento: date

    class Config:
        from_attributes = True
