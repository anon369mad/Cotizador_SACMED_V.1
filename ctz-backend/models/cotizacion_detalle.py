from sqlalchemy import (
    Column, Integer, DECIMAL, ForeignKey, TIMESTAMP, String
)
from models.base import Base

class CotizacionDetalle(Base):
    __tablename__ = "cotizacion_detalle"

    id_detalle = Column(Integer, primary_key=True)

    id_cotizacion = Column(Integer, ForeignKey("cotizaciones.id_cotizacion"))
    id_prestacion = Column(Integer, ForeignKey("prestaciones.id_prestacion"))
    descripcion= Column(String(255))
    cantidad = Column(Integer, nullable=False)
    valor_unitario = Column(DECIMAL(10,2))
    descuento = Column(DECIMAL(10,2))
    subtotal = Column(DECIMAL(12,2))
    total = Column(DECIMAL(12,2))

    created_at = Column(TIMESTAMP)
