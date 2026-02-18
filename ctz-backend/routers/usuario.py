from datetime import datetime, timedelta
from email.message import EmailMessage
from smtplib import SMTP, SMTPException
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.usuario import Usuario
from schemas.usuario import (
    PasswordRecoveryRequest,
    PasswordRecoveryTokenResponse,
    PasswordResetConfirm,
    UsuarioCreate,
    UsuarioLogin,
    UsuarioResponse,
    UsuarioUpdate,
)


router = APIRouter(tags=["Usuarios"])

# Almacenamiento temporal en memoria para tokens de recuperación.
# Estructura: {token: {"email": str, "expires_at": datetime}}
recovery_tokens: dict[str, dict[str, datetime | str]] = {}

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


@router.post("/password-recovery", response_model=PasswordRecoveryTokenResponse)
def request_password_recovery(data: PasswordRecoveryRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == data.email, Usuario.activo.is_(True)).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="No existe un usuario activo con ese correo")

    token = str(uuid4())
    recovery_tokens[token] = {
        "email": usuario.email,
        "expires_at": datetime.utcnow() + timedelta(minutes=30),
    }

    smtp_host = os.getenv("SMTP_HOST", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "25"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_sender = os.getenv("SMTP_SENDER", smtp_user or "no-reply@cotizador.local")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "false").lower() == "true"

    message = EmailMessage()
    message["Subject"] = "Token de recuperación de contraseña"
    message["From"] = smtp_sender
    message["To"] = usuario.email
    message.set_content(
        f"Hola,\n\nTu token de recuperación es: {token}\n"
        "Este token expira en 30 minutos.\n\n"
        "Si no solicitaste este cambio, ignora este mensaje."
    )

    try:
        with SMTP(host=smtp_host, port=smtp_port, timeout=10) as smtp:
            if smtp_use_tls:
                smtp.starttls()
            if smtp_user and smtp_password:
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)
    except (SMTPException, OSError, ValueError):
        recovery_tokens.pop(token, None)
        raise HTTPException(
            status_code=500,
            detail="No fue posible enviar el token al correo. Puede ser que el correo no exista.",
        )

    return PasswordRecoveryTokenResponse(
        message="Token de recuperación enviado correctamente al correo ingresado",
    )


@router.post("/password-reset")
def confirm_password_reset(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    token_data = recovery_tokens.get(data.token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Token inválido")

    expires_at = token_data["expires_at"]
    if datetime.utcnow() > expires_at:
        recovery_tokens.pop(data.token, None)
        raise HTTPException(status_code=400, detail="Token expirado")

    usuario = db.query(Usuario).filter(Usuario.email == token_data["email"]).first()
    if not usuario:
        recovery_tokens.pop(data.token, None)
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if len(data.new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres")

    usuario.password_hash = data.new_password.strip()
    db.commit()
    recovery_tokens.pop(data.token, None)

    return {"message": "Contraseña actualizada correctamente"}
