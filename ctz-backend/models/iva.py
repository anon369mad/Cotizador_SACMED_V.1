from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from models.base import Base

class Iva(Base):
    __tablename__ = "iva"

    id_iva = Column(Integer, primary_key=True, index=True)
    porcentaje = Column(DECIMAL(5,2), nullable=False)
    activo = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())