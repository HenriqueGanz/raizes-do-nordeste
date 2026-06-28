from __future__ import annotations

import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decodificar_token
from app.models.user import PapelUsuario, Usuario
from app.payments.processor import PaymentProcessor, criar_payment_processor

_bearer = HTTPBearer(auto_error=False)


def get_payment_processor() -> PaymentProcessor:
    return criar_payment_processor(settings.payment_gateway)


def get_current_user_opcional(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario | None:
    """funciona como get_current_user, mas devolve None se nenhum token foi enviado
    se um token FOR enviado e for invalido ou expirado, falha com 401
    """
    if cred is None:
        return None
    try:
        payload = decodificar_token(cred.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.") from exc

    usuario = db.get(Usuario, uuid.UUID(payload["sub"]))
    if usuario is None:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    return usuario


def get_current_user(
    usuario: Usuario | None = Depends(get_current_user_opcional),
) -> Usuario:
    if usuario is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    return usuario


def require_papel(*papeis: str):
    permitidos = {PapelUsuario(p) for p in papeis}

    def _checar(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.papel not in permitidos:
            raise HTTPException(status_code=403, detail="Acesso negado para este papel.")
        return usuario

    return _checar


def exigir_self_ou_admin(cliente_id: uuid.UUID, usuario: Usuario) -> None:
    """garante que o user é o próprio dono do recurso ou um ADMIN"""
    if usuario.papel != PapelUsuario.ADMIN and usuario.id != cliente_id:
        raise HTTPException(status_code=403, detail="Acesso negado a dados de outro cliente.")
