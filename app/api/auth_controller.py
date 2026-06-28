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
    """Faz login com email e senha e devolve um token. Copia esse token e cola no cadeado
    ("Authorize") aqui no Swagger pra conseguir testar as rotas que pedem login.

    Pra testar, já deixei 3 logins prontos no seed:
    - admin@raizesdonordeste.com.br / admin123 (ADMIN)
    - operador@raizesdonordeste.com.br / operador123 (OPERADOR)
    - demo@raizesdonordeste.com.br / cliente123 (CLIENTE, CPF 12345678900)
    """
    usuario = db.scalar(select(Usuario).where(Usuario.email == payload.email))
    if usuario is None or usuario.senha_hash is None or not verificar_senha(
        payload.senha, usuario.senha_hash
    ):
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    token = criar_token(str(usuario.id), usuario.papel.value)
    return TokenOut(access_token=token, papel=usuario.papel.value)
