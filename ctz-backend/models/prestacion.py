from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, TIMESTAMP, Text
from models.base import Base

class Prestacion(Base):
    __tablename__ = "prestaciones"

    id_prestacion = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False)
    valor_unitario = Column(DECIMAL(10,2), nullable=False)
    condiciones = Column(Text)
    activo = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
    clp = Column(Boolean, default=True)
