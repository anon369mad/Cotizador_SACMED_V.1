from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from models.conexion_capacitacion import ConexionCapacitacion
from schemas.conexion_capacitacion import (
    ConexionCapacitacionCreate,
    ConexionCapacitacionResponse,
    ConexionCapacitacionUpdate,
)

router = APIRouter(tags=["ConexionesCapacitacion"])


@router.post("/conexiones-capacitacion", response_model=ConexionCapacitacionResponse)
def crear_conexion_capacitacion(data: ConexionCapacitacionCreate, db: Session = Depends(get_db)):
    registro = ConexionCapacitacion(**data.dict())
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


@router.get("/conexiones-capacitacion", response_model=list[ConexionCapacitacionResponse])
def listar_conexiones_capacitacion(db: Session = Depends(get_db)):
    return (
        db.query(ConexionCapacitacion)
        .filter(ConexionCapacitacion.activo.is_(True))
        .order_by(ConexionCapacitacion.conexiones.asc())
        .all()
    )


@router.put("/conexiones-capacitacion/{id_conexion_capacitacion}", response_model=ConexionCapacitacionResponse)
def actualizar_conexion_capacitacion(
    id_conexion_capacitacion: int,
    data: ConexionCapacitacionUpdate,
    db: Session = Depends(get_db),
):
    registro = db.query(ConexionCapacitacion).get(id_conexion_capacitacion)
    if not registro:
        raise HTTPException(status_code=404, detail="Relación no encontrada")

    for campo, valor in data.dict(exclude_unset=True).items():
        setattr(registro, campo, valor)

    db.commit()
    db.refresh(registro)
    return registro


@router.delete("/conexiones-capacitacion/{id_conexion_capacitacion}")
def eliminar_conexion_capacitacion(id_conexion_capacitacion: int, db: Session = Depends(get_db)):
    registro = db.query(ConexionCapacitacion).get(id_conexion_capacitacion)
    if not registro:
        raise HTTPException(status_code=404, detail="Relación no encontrada")

    registro.activo = False
    db.commit()
    return {"ok": True, "message": "Relación desactivada correctamente"}
