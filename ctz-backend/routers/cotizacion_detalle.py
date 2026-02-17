from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.cotizacion_detalle import CotizacionDetalle
from schemas.cotizacion_detalle import CotizacionDetalleCreate, CotizacionDetalleResponse, CotizacionDetalleUpdate

router = APIRouter(tags=["Detalles de Cotización"])

@router.post("/cotizacion_detalles", response_model=CotizacionDetalleResponse)
def crear_detalle(data: CotizacionDetalleCreate, db: Session = Depends(get_db)):
    subtotal = data.cantidad * data.valor_unitario
    descuento_pct = max(0, min(100, data.descuento))
    total = subtotal * (1 - (descuento_pct / 100))

    detalle = CotizacionDetalle(
        id_cotizacion=data.id_cotizacion,
        id_prestacion=data.id_prestacion,
        cantidad=data.cantidad,
        descripcion=data.descripcion,
        valor_unitario=data.valor_unitario,
        descuento=descuento_pct,
        subtotal=subtotal,
        total=total,
    )
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

@router.put("/cotizacion_detalles/{id_detalle}", response_model=CotizacionDetalleResponse)
def actualizar_detalle(id_detalle: int, data: CotizacionDetalleUpdate, db: Session = Depends(get_db)):
    detalle = db.query(CotizacionDetalle).get(id_detalle)
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle no encontrado")
    for campo, valor in data.dict(exclude_unset=True).items():
        setattr(detalle, campo, valor)
    db.commit()
    db.refresh(detalle)
    return detalle

@router.delete("/cotizacion_detalles/{id_detalle}")
def eliminar_detalle(id_detalle: int, db: Session = Depends(get_db)):
    detalle = db.query(CotizacionDetalle).get(id_detalle)
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle no encontrado")
    db.delete(detalle)
    db.commit()
    return {"ok": True}
