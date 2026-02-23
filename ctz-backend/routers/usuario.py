from datetime import datetime, timedelta
from email.message import EmailMessage
import logging
import base64
import hashlib
import hmac
from smtplib import SMTP, SMTPException, SMTP_SSL
import os
from uuid import uuid4
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from models.usuario import Usuario
from schemas.usuario import (
    FirstAccessSetPasswordRequest,
    FirstAccessValidationRequest,
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
first_access_tokens: dict[str, dict[str, datetime | str]] = {}
ENCRYPTED_PREFIX = "enc::"
logger = logging.getLogger(__name__)


def build_inactive_email(user_id: int) -> str:
    return f"inactivo+{user_id}@disabled.local"


def clear_email_for_inactive_users(db: Session):
    inactive_users = (
        db.query(Usuario)
        .filter(Usuario.activo.is_(False), Usuario.email.isnot(None))
        .all()
    )

    for inactive_user in inactive_users:
        inactive_user.email = build_inactive_email(inactive_user.id_usuario)


def clear_tokens_for_email(email: str | None):
    if not email:
        return

    for token, token_data in list(first_access_tokens.items()):
        if token_data["email"] == email:
            first_access_tokens.pop(token, None)

    for token, token_data in list(recovery_tokens.items()):
        if token_data["email"] == email:
            recovery_tokens.pop(token, None)


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
    }


def generate_temporary_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_first_access_code(length: int = 6) -> str:
    digits = string.digits
    return "".join(secrets.choice(digits) for _ in range(length))


def get_first_access_token(email: str) -> tuple[str | None, dict[str, datetime | str] | None]:
    for token, token_data in list(first_access_tokens.items()):
        if token_data["email"] == email:
            if datetime.utcnow() > token_data["expires_at"]:
                first_access_tokens.pop(token, None)
                continue
            return token, token_data
    return None, None


def send_temporary_password_email(recipient_email: str, temporary_password: str, first_access_code: str):
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
    message["Subject"] = "Clave temporal de acceso"
    message["From"] = smtp_sender
    message["To"] = recipient_email
    message.set_content(
        "Hola,\n\n"
        "Se creó tu usuario en Cotizador.\n"
        f"Tu clave temporal es: {temporary_password}\n\n"
        "Tu código de validación para primer acceso es: "
        f"{first_access_code}\n\n"
        "Debes ingresar a la pantalla de Primer acceso y crear tu contraseña definitiva.\n"
        "Este flujo es distinto a Recuperar contraseña y aplica solo para tu primer ingreso.\n"
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
    clear_email_for_inactive_users(db)
    db.flush()

    existe = (
        db.query(Usuario)
        .filter(Usuario.email == data.email, Usuario.activo.is_(True))
        .first()
    )
    if existe:
        raise HTTPException(status_code=400, detail="Email ya registrado")

    plain_password = (data.password or "").strip() or generate_temporary_password()
    first_access_code = generate_first_access_code()
    if len(plain_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    usuario = Usuario(
        **data.dict(exclude={"password"}),
        password_hash=encrypt_password(plain_password),
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    first_access_tokens[first_access_code] = {
        "email": usuario.email,
        "expires_at": datetime.utcnow() + timedelta(hours=24),
    }

    try:
        send_temporary_password_email(usuario.email, plain_password, first_access_code)
    except (SMTPException, OSError, ValueError) as exc:
        logger.exception("Error enviando clave temporal para %s", usuario.email)
        raise HTTPException(
            status_code=500,
            detail=(
                "Usuario creado, pero no fue posible enviar la clave temporal al correo. "
                "Revisa la configuración SMTP (host, puerto, remitente, usuario, contraseña y TLS/SSL). "
                f"Detalle técnico: {exc}"
            ),
        )

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

    token, _ = get_first_access_token(usuario.email)
    if token:
        raise HTTPException(
            status_code=403,
            detail="Debes completar el flujo de primer acceso para crear tu contraseña definitiva.",
        )

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
        existe = (
            db.query(Usuario)
            .filter(
                Usuario.email == data.email,
                Usuario.id_usuario != id_usuario,
                Usuario.activo.is_(True),
            )
            .first()
        )
        if existe:
            raise HTTPException(status_code=400, detail="Email ya registrado")

    if data.password is not None and len(data.password.strip()) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    previous_email = usuario.email
    for campo, valor in data.dict(exclude_unset=True).items():
        if campo == "password":
            usuario.password_hash = encrypt_password(valor.strip())
            continue
        setattr(usuario, campo, valor)

    if usuario.activo is False:
        usuario.email = build_inactive_email(usuario.id_usuario)
        clear_tokens_for_email(previous_email)

    db.commit()
    db.refresh(usuario)
    return usuario_to_response(usuario)

@router.delete("/usuarios/{id_usuario}")
def eliminar_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).get(id_usuario)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    clear_tokens_for_email(usuario.email)
    usuario.activo = False
    usuario.email = build_inactive_email(usuario.id_usuario)
    db.commit()
    return {"ok": True, "message": "Usuario desactivado correctamente"}


@router.post("/first-access/validate")
def validate_first_access(data: FirstAccessValidationRequest, db: Session = Depends(get_db)):
    token_data = first_access_tokens.get(data.access_code.strip())
    if not token_data:
        raise HTTPException(status_code=400, detail="Código de primer acceso inválido")

    if datetime.utcnow() > token_data["expires_at"]:
        first_access_tokens.pop(data.access_code.strip(), None)
        raise HTTPException(status_code=400, detail="Código de primer acceso expirado")

    if token_data["email"] != data.email.strip():
        raise HTTPException(status_code=400, detail="El código no corresponde al correo ingresado")

    usuario = db.query(Usuario).filter(Usuario.email == data.email.strip(), Usuario.activo.is_(True)).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {"message": "Código validado correctamente"}


@router.post("/first-access/set-password")
def set_first_access_password(data: FirstAccessSetPasswordRequest, db: Session = Depends(get_db)):
    token = data.access_code.strip()
    token_data = first_access_tokens.get(token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Código de primer acceso inválido")

    if datetime.utcnow() > token_data["expires_at"]:
        first_access_tokens.pop(token, None)
        raise HTTPException(status_code=400, detail="Código de primer acceso expirado")

    email = data.email.strip()
    if token_data["email"] != email:
        raise HTTPException(status_code=400, detail="El código no corresponde al correo ingresado")

    if len(data.new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres")

    usuario = db.query(Usuario).filter(Usuario.email == email, Usuario.activo.is_(True)).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.password_hash = encrypt_password(data.new_password.strip())
    db.commit()
    first_access_tokens.pop(token, None)

    return {"message": "Contraseña creada correctamente. Ya puedes iniciar sesión."}


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
