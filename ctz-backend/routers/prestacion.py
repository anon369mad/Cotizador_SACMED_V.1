from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.prestacion import Prestacion
from schemas.prestacion import PrestacionCreate, PrestacionResponse, PrestacionUpdate

router = APIRouter(tags=["Prestaciones"])

@router.post("/prestaciones", response_model=PrestacionResponse)
def crear_prestacion(data: PrestacionCreate, db: Session = Depends(get_db)):
    existe = db.query(Prestacion).filter(Prestacion.nombre == data.nombre).first()
    if existe:
        raise HTTPException(status_code=400, detail="Prestación ya existe")
    prestacion = Prestacion(**data.dict())
    db.add(prestacion)
    db.commit()
    db.refresh(prestacion)
    return prestacion

@router.get("/prestaciones", response_model=list[PrestacionResponse])
def listar_prestaciones(db: Session = Depends(get_db)):
    return db.query(Prestacion).all()

@router.get("/prestaciones/{id_prestacion}", response_model=PrestacionResponse)
def obtener_prestacion(id_prestacion: int, db: Session = Depends(get_db)):
    prestacion = db.query(Prestacion).get(id_prestacion)
    if not prestacion:
        raise HTTPException(status_code=404, detail="Prestación no encontrada")
    return prestacion

@router.put("/prestaciones/{id_prestacion}", response_model=PrestacionResponse)
def actualizar_prestacion(id_prestacion: int, data: PrestacionUpdate, db: Session = Depends(get_db)):
    prestacion = db.query(Prestacion).get(id_prestacion)
    if not prestacion:
        raise HTTPException(status_code=404, detail="Prestación no encontrada")
    if data.nombre:
        existe = db.query(Prestacion).filter(Prestacion.nombre == data.nombre, Prestacion.id_prestacion != id_prestacion).first()
        if existe:
            raise HTTPException(status_code=400, detail="Nombre de prestación ya existe")
    for campo, valor in data.dict(exclude_unset=True).items():
        setattr(prestacion, campo, valor)
    db.commit()
    db.refresh(prestacion)
    return prestacion

@router.delete("/prestaciones/{id_prestacion}")
def eliminar_prestacion(id_prestacion: int, db: Session = Depends(get_db)):
    prestacion = db.query(Prestacion).get(id_prestacion)
    if not prestacion:
        raise HTTPException(status_code=404, detail="Prestación no encontrada")
    db.delete(prestacion)
    db.commit()
    return {"ok": True}
