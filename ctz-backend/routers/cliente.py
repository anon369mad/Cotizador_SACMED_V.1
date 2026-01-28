from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.cliente import Cliente
from schemas.cliente import ClienteCreate, ClienteResponse, ClienteUpdate

router = APIRouter(tags=["Clientes"])

@router.post("/clientes", response_model=ClienteResponse)
def crear_cliente(data: ClienteCreate, db: Session = Depends(get_db)):
    existe = db.query(Cliente).filter(Cliente.rut == data.rut).first()
    if existe:
        raise HTTPException(status_code=400, detail="Cliente ya existe")

    cliente = Cliente(**data.dict())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    return cliente

@router.get("/clientes", response_model=list[ClienteResponse])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(Cliente).all()

@router.get("/clientes/{id_cliente}", response_model=ClienteResponse)
def obtener_cliente(id_cliente: int, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).get(id_cliente)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente

@router.delete("/clientes/{id_cliente}")
def eliminar_cliente(id_cliente: int, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).get(id_cliente)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    db.delete(cliente)
    db.commit()
    return {"ok": True}

@router.put("/clientes/{id_cliente}", response_model=ClienteResponse)
def actualizar_cliente(
    id_cliente: int,
    data: ClienteUpdate,
    db: Session = Depends(get_db)
):
    cliente = db.query(Cliente).get(id_cliente)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if data.rut:
        existe = (
            db.query(Cliente)
            .filter(Cliente.rut == data.rut, Cliente.id_cliente != id_cliente)
            .first()
        )
        if existe:
            raise HTTPException(status_code=400, detail="RUT ya existe")

    for campo, valor in data.dict(exclude_unset=True).items():
        setattr(cliente, campo, valor)

    db.commit()
    db.refresh(cliente)
    return cliente
