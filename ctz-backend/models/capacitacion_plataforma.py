from sqlalchemy import Boolean, Column, Integer, TIMESTAMP

from models.base import Base


class CapacitacionPlataforma(Base):
    __tablename__ = "capacitaciones_plataforma"

    id_capacitacion_plataforma = Column(Integer, primary_key=True)
    conexiones_desde = Column(Integer, nullable=False)
    conexiones_hasta = Column(Integer, nullable=True)
    horas_capacitacion = Column(Integer, nullable=False)
    activo = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
