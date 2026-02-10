from pydantic import BaseModel
from typing import Optional
from datetime import date
# un schema es una representación estructurada de los datos que se utilizan para validar y serializar la información que se intercambia entre el cliente y el servidor en una API.
#mas simplemente, los schemas definen cómo deben lucir los datos que se envían y reciben, asegurando que cumplan con ciertos formatos y tipos antes de ser procesados o almacenados.
class CotizacionBase(BaseModel):
    tipo: Optional[str] = None
    id_cliente: Optional[int] = None
    nombre_cliente: Optional[str] = None
    rut_cliente: Optional[str] = None
    id_usuario: Optional[int] = None
    id_iva: Optional[int] = None
    meses: Optional[int] = None
    conexiones: Optional[int] = None

    subtotal: Optional[float] = None
    descuento_total: Optional[float] = None
    iva_monto: Optional[float] = None
    total: Optional[float] = None

    condiciones_adicionales: Optional[str] = None

class CotizacionCreate(CotizacionBase):
    pass

class CotizacionUpdate(BaseModel):
    estado: Optional[str]
    condiciones_adicionales: Optional[str]

class CotizacionResponse(CotizacionBase):
    id_cotizacion: int
    subtotal: Optional[float] = None
    descuento_total: Optional[float] = None
    iva_monto: Optional[float] = None
    total: Optional[float] = None
    estado: Optional[str] = None
    fecha_emision: Optional[date] = None
    fecha_vencimiento: Optional[date] = None

    class Config:
        from_attributes = True
