from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.iva import Iva
from schemas.iva import IvaCreate, IvaResponse, IvaUpdate

router = APIRouter(tags=["IVA"])

@router.post("/iva", response_model=IvaResponse)
def crear_iva(data: IvaCreate, db: Session = Depends(get_db)):
    existe = db.query(Iva).filter(Iva.nombre == data.nombre).first()
    if existe:
        raise HTTPException(status_code=400, detail="IVA ya existe")
    iva = Iva(**data.dict())
    db.add(iva)
    db.commit()
    db.refresh(iva)
    return iva

@router.get("/iva", response_model=list[IvaResponse])
def listar_iva(db: Session = Depends(get_db)):
    return db.query(Iva).all()

@router.get("/iva/{id_iva}", response_model=IvaResponse)
def obtener_iva(id_iva: int, db: Session = Depends(get_db)):
    iva = db.query(Iva).get(id_iva)
    if not iva:
        raise HTTPException(status_code=404, detail="IVA no encontrado")
    return iva

@router.put("/iva/{id_iva}", response_model=IvaResponse)
def actualizar_iva(id_iva: int, data: IvaUpdate, db: Session = Depends(get_db)):
    iva = db.query(Iva).get(id_iva)
    if not iva:
        raise HTTPException(status_code=404, detail="IVA no encontrado")
    for campo, valor in data.dict(exclude_unset=True).items():
        setattr(iva, campo, valor)
    db.commit()
    db.refresh(iva)
    return iva

@router.delete("/iva/{id_iva}")
def eliminar_iva(id_iva: int, db: Session = Depends(get_db)):
    iva = db.query(Iva).get(id_iva)
    if not iva:
        raise HTTPException(status_code=404, detail="IVA no encontrado")
    db.delete(iva)
    db.commit()
    return {"ok": True}
