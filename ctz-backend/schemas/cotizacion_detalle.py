from pydantic import BaseModel, Field
from typing import Optional

class CotizacionDetalleBase(BaseModel):
    id_cotizacion: int
    id_prestacion: Optional[int] = None
    descripcion: Optional[str] = Field(default=None, validation_alias="descripcion_manual")
    cantidad: int
    valor_unitario: float
    descuento: float = 0

class CotizacionDetalleCreate(CotizacionDetalleBase):
    pass

class CotizacionDetalleResponse(CotizacionDetalleBase):
    id_detalle: int
    subtotal: Optional[float] = None
    total: Optional[float] = None

    class Config:
        from_attributes = True

class CotizacionDetalleUpdate(BaseModel):
    cantidad: Optional[int]
    descuento: Optional[float]
