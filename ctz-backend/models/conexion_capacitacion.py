from sqlalchemy import Boolean, Column, Integer, TIMESTAMP
from models.base import Base


class ConexionCapacitacion(Base):
    __tablename__ = "conexiones_capacitacion"

    id_conexion_capacitacion = Column(Integer, primary_key=True)
    conexiones = Column(Integer, nullable=False)
    gigabytes_almacenamiento = Column(Integer, nullable=False)
    activo = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
