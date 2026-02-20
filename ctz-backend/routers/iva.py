from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.iva import Iva
from schemas.iva import IvaCreate, IvaResponse, IvaUpdate

router = APIRouter(tags=["IVA"])

@router.post("/iva", response_model=IvaResponse)
def crear_iva(data: IvaCreate, db: Session = Depends(get_db)):
    payload = data.dict()
    if payload.get("activo", True):
        db.query(Iva).filter(Iva.activo.is_(True)).update({"activo": False})

    iva = Iva(**payload)
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
    iva_actual = db.query(Iva).get(id_iva)
    if not iva_actual:
        raise HTTPException(status_code=404, detail="IVA no encontrado")

    payload = data.dict(exclude_unset=True)
    nuevo_porcentaje = payload.get("porcentaje", iva_actual.porcentaje)
    nuevo_activo = payload.get("activo", True)

    if nuevo_activo:
        db.query(Iva).filter(Iva.activo.is_(True)).update({"activo": False})
    else:
        iva_actual.activo = False

    nuevo_iva = Iva(
        porcentaje=nuevo_porcentaje,
        activo=nuevo_activo,
    )
    db.add(nuevo_iva)
    db.commit()
    db.refresh(nuevo_iva)
    return nuevo_iva

@router.delete("/iva/{id_iva}")
def eliminar_iva(id_iva: int, db: Session = Depends(get_db)):
    iva = db.query(Iva).get(id_iva)
    if not iva:
        raise HTTPException(status_code=404, detail="IVA no encontrado")
    db.delete(iva)
    db.commit()
    return {"ok": True}
