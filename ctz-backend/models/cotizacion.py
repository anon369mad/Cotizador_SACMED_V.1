from sqlalchemy import (
    Column, Integer, DECIMAL, Enum, TIMESTAMP,
    Date, Text, ForeignKey,String
)
from models.base import Base
#Los models son las tablas de la base de datos representadas en código Python usando SQLAlchemy ORM.
#Sirve para definir la estructura de la tabla "cotizaciones" y sus columnas.
#EStoy ayuda a interactuar con la base de datos de manera más sencilla y estructurada.
#La esencia es mapear las tablas de la base de datos a clases de Python.
class Cotizacion(Base):
    __tablename__ = "cotizaciones"
    id_cotizacion = Column(Integer, primary_key=True)
    tipo = Column(String)
    id_cliente = Column(Integer, ForeignKey("clientes.id_cliente"))
    nombre_cliente = Column(String(255))
    rut_cliente = Column(String(20))
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"))
    meses = Column(Integer)
    conexiones = Column(Integer)

    subtotal = Column(DECIMAL(12,2))
    descuento_total = Column(DECIMAL(12,2))
    total = Column(DECIMAL(12,2))

    condiciones_adicionales = Column(Text)

    estado = Column(Enum("BORRADOR", "CONFIRMADA"), default="BORRADOR")

    fecha_emision = Column(Date)
    fecha_vencimiento = Column(Date)
    id_iva = Column(Integer, ForeignKey("iva.id_iva"))
    iva_monto = Column(DECIMAL(12,2))
    firma_cliente = Column(String(255))

    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)
