from datetime import datetime, timedelta
from email.message import EmailMessage
import logging
import base64
import hashlib
import hmac
from smtplib import SMTP, SMTPException, SMTP_SSL
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
ENCRYPTED_PREFIX = "enc::"
logger = logging.getLogger(__name__)


def _env_first(*keys: str, default: str | None = None) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value is not None and value.strip() != "":
            return value.strip()
    return default


def _encryption_key() -> bytes:
    return os.getenv("PASSWORD_ENCRYPTION_KEY", "cotizador-dev-secret-key").encode("utf-8")


def _build_keystream(length: int, key: bytes) -> bytes:
    stream = b""
    counter = 0
    while len(stream) < length:
        stream += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    return stream[:length]


def encrypt_password(plain_password: str) -> str:
    plain_bytes = plain_password.encode("utf-8")
    key = _encryption_key()
    keystream = _build_keystream(len(plain_bytes), key)
    encrypted_bytes = bytes(byte ^ keystream[index] for index, byte in enumerate(plain_bytes))
    token = base64.urlsafe_b64encode(encrypted_bytes).decode("utf-8")
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_password(stored_password: str) -> str:
    if not stored_password.startswith(ENCRYPTED_PREFIX):
        return stored_password

    token = stored_password[len(ENCRYPTED_PREFIX):]
    encrypted_bytes = base64.urlsafe_b64decode(token.encode("utf-8"))
    key = _encryption_key()
    keystream = _build_keystream(len(encrypted_bytes), key)
    plain_bytes = bytes(byte ^ keystream[index] for index, byte in enumerate(encrypted_bytes))
    return plain_bytes.decode("utf-8")


def verify_password(stored_password: str, plain_password: str) -> bool:
    try:
        decrypted = decrypt_password(stored_password)
    except (ValueError, UnicodeDecodeError):
        return False
    return hmac.compare_digest(decrypted, plain_password)


def usuario_to_response(usuario: Usuario) -> dict:
    return {
        "id_usuario": usuario.id_usuario,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
        "activo": usuario.activo,
        "password": decrypt_password(usuario.password_hash),
    }


def send_recovery_email(recipient_email: str, token: str):
    smtp_host = _env_first("SMTP_HOST", "MAIL_HOST")
    smtp_port_raw = _env_first("SMTP_PORT", "MAIL_PORT", default="587")
    smtp_user = _env_first("SMTP_USER", "MAIL_USERNAME")
    smtp_password = _env_first("SMTP_PASSWORD", "MAIL_PASSWORD")
    smtp_sender = _env_first("SMTP_SENDER", "MAIL_FROM_ADDRESS", default=smtp_user)
    smtp_use_tls = _env_first("SMTP_USE_TLS", "MAIL_USE_TLS", default="true").lower() == "true"
    smtp_use_ssl = _env_first("SMTP_USE_SSL", "MAIL_USE_SSL", default="false").lower() == "true"

    if not smtp_host:
        raise ValueError("Falta configurar SMTP_HOST (o MAIL_HOST).")

    try:
        smtp_port = int(smtp_port_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("SMTP_PORT debe ser un número válido.") from exc

    if not smtp_sender:
        raise ValueError("Falta configurar SMTP_SENDER (o MAIL_FROM_ADDRESS).")

    message = EmailMessage()
    message["Subject"] = "Token de recuperación de contraseña"
    message["From"] = smtp_sender
    message["To"] = recipient_email
    message.set_content(
        f"Hola,\n\nTu token de recuperación es: {token}\n"
        "Este token expira en 30 minutos.\n\n"
        "Si no solicitaste este cambio, ignora este mensaje."
    )

    smtp_client = SMTP_SSL if smtp_use_ssl else SMTP

    with smtp_client(host=smtp_host, port=smtp_port, timeout=15) as smtp:
        if smtp_use_tls and not smtp_use_ssl:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
        if smtp_user and smtp_password:
            smtp.login(smtp_user, smtp_password)
        smtp.send_message(message)

@router.post("/usuarios", response_model=UsuarioResponse)
def crear_usuario(data: UsuarioCreate, db: Session = Depends(get_db)):
    existe = db.query(Usuario).filter(Usuario.email == data.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    if len(data.password.strip()) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    usuario = Usuario(
        **data.dict(exclude={"password"}),
        password_hash=encrypt_password(data.password.strip()),
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario_to_response(usuario)

@router.post("/login", response_model=UsuarioResponse)
def login(data: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = (
        db.query(Usuario)
        .filter(Usuario.email == data.email, Usuario.activo.is_(True))
        .first()
    )
    if not usuario or not verify_password(usuario.password_hash, data.password.strip()):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return usuario_to_response(usuario)

@router.get("/usuarios", response_model=list[UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    usuarios = db.query(Usuario).filter(Usuario.activo.is_(True)).all()
    return [usuario_to_response(usuario) for usuario in usuarios]

@router.get("/usuarios/{id_usuario}", response_model=UsuarioResponse)
def obtener_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).get(id_usuario)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario_to_response(usuario)

@router.put("/usuarios/{id_usuario}", response_model=UsuarioResponse)
def actualizar_usuario(id_usuario: int, data: UsuarioUpdate, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).get(id_usuario)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if data.email:
        existe = db.query(Usuario).filter(Usuario.email == data.email, Usuario.id_usuario != id_usuario).first()
        if existe:
            raise HTTPException(status_code=400, detail="Email ya registrado")

    if data.password is not None and len(data.password.strip()) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    for campo, valor in data.dict(exclude_unset=True).items():
        if campo == "password":
            usuario.password_hash = encrypt_password(valor.strip())
            continue
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario_to_response(usuario)

@router.delete("/usuarios/{id_usuario}")
def eliminar_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).get(id_usuario)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    usuario.activo = False
    db.commit()
    return {"ok": True, "message": "Usuario desactivado correctamente"}


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

    try:
        send_recovery_email(usuario.email, token)
    except (SMTPException, OSError, ValueError) as exc:
        logger.exception("Error enviando token de recuperación para %s", usuario.email)
        recovery_tokens.pop(token, None)
        raise HTTPException(
            status_code=500,
            detail=(
                "No fue posible enviar el token al correo. "
                "Revisa la configuración SMTP (host, puerto, remitente, usuario, contraseña y TLS/SSL). "
                f"Detalle técnico: {exc}"
            ),
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

    usuario.password_hash = encrypt_password(data.new_password.strip())
    db.commit()
    recovery_tokens.pop(data.token, None)

    return {"message": "Contraseña actualizada correctamente"}
