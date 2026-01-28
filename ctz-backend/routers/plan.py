from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.plan import Plan
from schemas.plan import PlanCreate, PlanResponse, PlanUpdate

router = APIRouter(tags=["Planes"])

@router.post("/planes", response_model=PlanResponse)
def crear_plan(data: PlanCreate, db: Session = Depends(get_db)):
    existe = db.query(Plan).filter(Plan.nombre == data.nombre).first()
    if existe:
        raise HTTPException(status_code=400, detail="Plan ya existe")
    plan = Plan(**data.dict())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@router.get("/planes", response_model=list[PlanResponse])
def listar_planes(db: Session = Depends(get_db)):
    return db.query(Plan).all()

@router.get("/planes/{id_plan}", response_model=PlanResponse)
def obtener_plan(id_plan: int, db: Session = Depends(get_db)):
    plan = db.query(Plan).get(id_plan)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    return plan

@router.put("/planes/{id_plan}", response_model=PlanResponse)
def actualizar_plan(id_plan: int, data: PlanUpdate, db: Session = Depends(get_db)):
    plan = db.query(Plan).get(id_plan)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    # Validación de nombre único
    if data.nombre:
        existe = db.query(Plan).filter(Plan.nombre == data.nombre, Plan.id_plan != id_plan).first()
        if existe:
            raise HTTPException(status_code=400, detail="Nombre de plan ya existe")
    for campo, valor in data.dict(exclude_unset=True).items():
        setattr(plan, campo, valor)
    db.commit()
    db.refresh(plan)
    return plan

@router.delete("/planes/{id_plan}")
def eliminar_plan(id_plan: int, db: Session = Depends(get_db)):
    plan = db.query(Plan).get(id_plan)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    db.delete(plan)
    db.commit()
    return {"ok": True}
