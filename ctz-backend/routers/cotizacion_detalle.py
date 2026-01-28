from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.cotizacion_detalle import CotizacionDetalle
from schemas.cotizacion_detalle import CotizacionDetalleCreate, CotizacionDetalleResponse

router = APIRouter(tags=["Detalles de Cotización"])

@router.post("/cotizacion_detalles", response_model=CotizacionDetalleResponse)
def crear_detalle(data: CotizacionDetalleCreate, db: Session = Depends(get_db)):
    detalle = CotizacionDetalle(**data.dict())
    db.add(detalle)
    db.commit()
    db.refresh(detalle)
    return detalle

@router.get("/cotizacion_detalles", response_model=list[CotizacionDetalleResponse])
def listar_detalles(db: Session = Depends(get_db)):
    return db.query(CotizacionDetalle).all()

@router.get("/cotizacion_detalles/{id_detalle}", response_model=CotizacionDetalleResponse)
def obtener_detalle(id_detalle: int, db: Session = Depends(get_db)):
    detalle = db.query(CotizacionDetalle).get(id_detalle)
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle no encontrado")
    return detalle

@router.delete("/cotizacion_detalles/{id_detalle}")
def eliminar_detalle(id_detalle: int, db: Session = Depends(get_db)):
    detalle = db.query(CotizacionDetalle).get(id_detalle)
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle no encontrado")
    db.delete(detalle)
    db.commit()
    return {"ok": True}
