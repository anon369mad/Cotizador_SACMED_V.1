from sqlalchemy import Column, Integer, String, TIMESTAMP
from models.base import Base

class Cliente(Base):
    __tablename__ = "clientes"

    id_cliente = Column(Integer, primary_key=True)
    razon_social = Column(String(150), nullable=False)
    rut = Column(String(20), nullable=False, unique=True)
    created_at = Column(TIMESTAMP)
