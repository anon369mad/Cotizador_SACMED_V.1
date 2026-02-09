from pydantic import BaseModel, EmailStr
from typing import Optional

class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    rol: str
    activo: bool = True

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class UsuarioUpdate(BaseModel):
    nombre: Optional[str]
    email: Optional[EmailStr]
    rol: Optional[str]
    activo: Optional[bool]

class UsuarioResponse(UsuarioBase):
    id_usuario: int

    class Config:
        from_attributes = True
