from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from models.capacitacion_plataforma import CapacitacionPlataforma
from schemas.capacitacion_plataforma import (
    CapacitacionPlataformaCreate,
    CapacitacionPlataformaResponse,
    CapacitacionPlataformaUpdate,
)

router = APIRouter(tags=["CapacitacionPlataforma"])


@router.post("/capacitaciones-plataforma", response_model=CapacitacionPlataformaResponse)
def crear_capacitacion_plataforma(data: CapacitacionPlataformaCreate, db: Session = Depends(get_db)):
    registro = CapacitacionPlataforma(**data.dict())
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


@router.get("/capacitaciones-plataforma", response_model=list[CapacitacionPlataformaResponse])
def listar_capacitaciones_plataforma(db: Session = Depends(get_db)):
    return (
        db.query(CapacitacionPlataforma)
        .filter(CapacitacionPlataforma.activo.is_(True))
        .order_by(CapacitacionPlataforma.conexiones_desde.asc())
        .all()
    )


@router.put("/capacitaciones-plataforma/{id_capacitacion_plataforma}", response_model=CapacitacionPlataformaResponse)
def actualizar_capacitacion_plataforma(
    id_capacitacion_plataforma: int,
    data: CapacitacionPlataformaUpdate,
    db: Session = Depends(get_db),
):
    registro = db.query(CapacitacionPlataforma).get(id_capacitacion_plataforma)
    if not registro:
        raise HTTPException(status_code=404, detail="Relación no encontrada")

    for campo, valor in data.dict(exclude_unset=True).items():
        setattr(registro, campo, valor)

    db.commit()
    db.refresh(registro)
    return registro


@router.delete("/capacitaciones-plataforma/{id_capacitacion_plataforma}")
def eliminar_capacitacion_plataforma(id_capacitacion_plataforma: int, db: Session = Depends(get_db)):
    registro = db.query(CapacitacionPlataforma).get(id_capacitacion_plataforma)
    if not registro:
        raise HTTPException(status_code=404, detail="Relación no encontrada")

    registro.activo = False
    db.commit()
    return {"ok": True, "message": "Relación desactivada correctamente"}
