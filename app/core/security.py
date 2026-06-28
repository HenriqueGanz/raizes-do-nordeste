from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings

def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode()[:72], bcrypt.gensalt()).decode()

def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode()[:72], senha_hash.encode())

def criar_token(usuario_id: str, papel: str) -> str:
    expira = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": usuario_id, "papel": papel, "exp": expira}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decodificar_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])