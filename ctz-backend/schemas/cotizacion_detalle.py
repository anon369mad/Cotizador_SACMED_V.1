from pydantic import BaseModel
from typing import Optional

class CotizacionDetalleBase(BaseModel):
    id_prestacion: Optional[int]
    descripcion_manual: Optional[str]
    cantidad: int
    valor_unitario: float
    descuento: float = 0

class CotizacionDetalleCreate(CotizacionDetalleBase):
    pass

class CotizacionDetalleResponse(CotizacionDetalleBase):
    id_detalle: int
    subtotal: float
    total: float

    class Config:
        from_attributes = True

class CotizacionDetalleUpdate(BaseModel):
    cantidad: Optional[int]
    descuento: Optional[float]
