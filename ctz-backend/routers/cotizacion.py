from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.cotizacion import Cotizacion
from models.usuario import Usuario
from schemas.cotizacion import CotizacionCreate, CotizacionResponse, CotizacionUpdate
from models.cotizacion_detalle import CotizacionDetalle

router = APIRouter(tags=["Cotizaciones"])


def attach_user_names(cotizaciones: list[Cotizacion], db: Session):
    user_ids = {cot.id_usuario for cot in cotizaciones if cot.id_usuario is not None}
    if not user_ids:
        return cotizaciones

    usuarios = (
        db.query(Usuario.id_usuario, Usuario.nombre)
        .filter(Usuario.id_usuario.in_(user_ids))
        .all()
    )
    nombres_por_id = {id_usuario: nombre for id_usuario, nombre in usuarios}

    for cot in cotizaciones:
        cot.nombre_usuario = nombres_por_id.get(cot.id_usuario)

    return cotizaciones


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
    cotizaciones = db.query(Cotizacion).all()
    return attach_user_names(cotizaciones, db)

@router.get("/cotizaciones/{id_cotizacion}", response_model=CotizacionResponse)
def obtener_cotizacion(id_cotizacion: int, db: Session = Depends(get_db)):
    cotizacion = db.query(Cotizacion).get(id_cotizacion)
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    attach_user_names([cotizacion], db)
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

    if cotizacion.estado == "CONFIRMADA":
        raise HTTPException(status_code=400, detail="Las cotizaciones confirmadas no se pueden eliminar")

    # 🔥 borrar detalles primero
    db.query(CotizacionDetalle)\
        .filter(CotizacionDetalle.id_cotizacion == id_cotizacion)\
        .delete()

    # luego borrar la cotización
    db.delete(cotizacion)

    db.commit()
    return {"ok": True}
