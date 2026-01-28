from sqlalchemy.orm import Session
from models.cliente import Cliente

def get_clientes(db: Session):
    return db.query(Cliente).all()
