from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, TIMESTAMP, Text
from models.base import Base

class Plan(Base):
    __tablename__ = "planes"

    id_plan = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    conexiones_incluidas = Column(Integer, nullable=False)
    valor_plan_mensual = Column(DECIMAL(10,2), nullable=False)
    valor_conexion_adicional = Column(DECIMAL(10,2), nullable=False)
    condiciones = Column(Text)
    mensajes_whatsapp = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
