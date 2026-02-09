from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.usuario import Usuario
from schemas.usuario import UsuarioCreate, UsuarioLogin, UsuarioResponse, UsuarioUpdate

router = APIRouter(tags=["Usuarios"])

@router.post("/usuarios", response_model=UsuarioResponse)
def crear_usuario(data: UsuarioCreate, db: Session = Depends(get_db)):
    existe = db.query(Usuario).filter(Usuario.email == data.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    usuario = Usuario(**data.dict(exclude={"password"}), password_hash=data.password)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario

@router.post("/login", response_model=UsuarioResponse)
def login(data: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = (
        db.query(Usuario)
        .filter(
            Usuario.email == data.email,
            Usuario.password_hash == data.password,
            Usuario.activo.is_(True),
        )
        .first()
    )
    if not usuario:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return usuario

@router.get("/usuarios", response_model=list[UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuario).all()

@router.get("/usuarios/{id_usuario}", response_model=UsuarioResponse)
def obtener_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).get(id_usuario)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@router.put("/usuarios/{id_usuario}", response_model=UsuarioResponse)
def actualizar_usuario(id_usuario: int, data: UsuarioUpdate, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).get(id_usuario)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if data.email:
        existe = db.query(Usuario).filter(Usuario.email == data.email, Usuario.id_usuario != id_usuario).first()
        if existe:
            raise HTTPException(status_code=400, detail="Email ya registrado")
    for campo, valor in data.dict(exclude_unset=True).items():
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario

@router.delete("/usuarios/{id_usuario}")
def eliminar_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).get(id_usuario)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(usuario)
    db.commit()
    return {"ok": True}
