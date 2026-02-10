from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.cotizacion import Cotizacion
from schemas.cotizacion import CotizacionCreate, CotizacionResponse, CotizacionUpdate

router = APIRouter(tags=["Cotizaciones"])

@router.post("/cotizaciones", response_model=CotizacionResponse)
def crear_cotizacion(data: CotizacionCreate, db: Session = Depends(get_db)):
    cotizacion = Cotizacion(**data.dict())
    cotizacion.fecha_emision = date.today()
    cotizacion.fecha_vencimiento = date.today() + timedelta(days=30)
    db.add(cotizacion)
    db.commit()
    db.refresh(cotizacion)
    return cotizacion

@router.get("/cotizaciones", response_model=list[CotizacionResponse])
def listar_cotizaciones(db: Session = Depends(get_db)):
    return db.query(Cotizacion).all()

@router.get("/cotizaciones/{id_cotizacion}", response_model=CotizacionResponse)
def obtener_cotizacion(id_cotizacion: int, db: Session = Depends(get_db)):
    cotizacion = db.query(Cotizacion).get(id_cotizacion)
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return cotizacion

@router.put("/cotizaciones/{id_cotizacion}", response_model=CotizacionResponse)
def actualizar_cotizacion(id_cotizacion: int, data: CotizacionUpdate, db: Session = Depends(get_db)):
    cotizacion = db.query(Cotizacion).get(id_cotizacion)
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    for campo, valor in data.dict(exclude_unset=True).items():
        setattr(cotizacion, campo, valor)
    db.commit()
    db.refresh(cotizacion)
    return cotizacion

@router.delete("/cotizaciones/{id_cotizacion}")
def eliminar_cotizacion(id_cotizacion: int, db: Session = Depends(get_db)):
    cotizacion = db.query(Cotizacion).get(id_cotizacion)
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    db.delete(cotizacion)
    db.commit()
    return {"ok": True}
