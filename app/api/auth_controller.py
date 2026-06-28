from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import criar_token, verificar_senha
from app.models.user import Usuario
from app.schemas.auth import LoginIn, TokenOut

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    usuario = db.scalar(select(Usuario).where(Usuario.email == payload.email))
    if usuario is None or usuario.senha_hash is None or not verificar_senha(
        payload.senha, usuario.senha_hash
    ):
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    token = criar_token(str(usuario.id), usuario.papel.value)
    return TokenOut(access_token=token, papel=usuario.papel.value)
