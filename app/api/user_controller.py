from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_self_ou_admin, get_current_user
from app.core.database import get_db
from app.models.catalog import AuditLog
from app.models.order import Pedido
from app.models.user import Usuario
from app.schemas.user import (
    ClienteCreate,
    ClienteOut,
    ClienteUpdate,
    PedidoResumo,
    ResgateIn,
    ResgateOut,
)
from app.services import loyalty_service, user_service

router = APIRouter(prefix="/v1/clientes", tags=["clientes"])


def _to_out(cliente: Usuario) -> ClienteOut:
    return ClienteOut(
        cliente_id=cliente.id,
        nome=cliente.nome,
        email=cliente.email,
        cpf=cliente.cpf,
        pontos_fidelidade=cliente.pontos_fidelidade,
        papel=cliente.papel.value,
    )


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def cadastrar_cliente(payload: ClienteCreate, db: Session = Depends(get_db)) -> ClienteOut:
    """auto-cadastro e cliente para uso no aplicativo"""
    if db.scalar(select(Usuario).where(Usuario.email == payload.email)) is not None:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
    if payload.cpf and user_service.buscar_por_cpf(db, payload.cpf) is not None:
        raise HTTPException(status_code=409, detail="CPF já cadastrado.")

    cliente = user_service.criar_cliente(db, payload)
    db.commit()
    db.refresh(cliente)
    return _to_out(cliente)


@router.get("/{cliente_id}", response_model=ClienteOut)
def obter_cliente(
    cliente_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ClienteOut:
    exigir_self_ou_admin(cliente_id, usuario)
    cliente = user_service.obter_cliente(db, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return _to_out(cliente)


@router.put("/{cliente_id}", response_model=ClienteOut)
def atualizar_cliente(
    cliente_id: uuid.UUID,
    payload: ClienteUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ClienteOut:
    exigir_self_ou_admin(cliente_id, usuario)
    cliente = user_service.obter_cliente(db, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    user_service.atualizar_cliente(db, cliente, payload)
    db.commit()
    db.refresh(cliente)
    return _to_out(cliente)


@router.delete("/{cliente_id}", status_code=status.HTTP_200_OK)
def anonimizar_cliente(
    cliente_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> dict:
    """LGPD remove os dados pessoais do cliente"""
    exigir_self_ou_admin(cliente_id, usuario)
    cliente = user_service.obter_cliente(db, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    cliente.anonimizar()
    db.add(
        AuditLog(
            ator_id=usuario.id,
            acao="ANONIMIZAR_CLIENTE",
            entidade="usuario",
            detalhes={"cliente_id": str(cliente_id)},
        )
    )
    db.commit()
    return {"cliente_id": str(cliente_id), "anonimizado": True}


@router.get("/{cliente_id}/pedidos", response_model=list[PedidoResumo])
def historico_pedidos(
    cliente_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[PedidoResumo]:
    exigir_self_ou_admin(cliente_id, usuario)
    pedidos = db.scalars(
        select(Pedido).where(Pedido.usuario_id == cliente_id).order_by(Pedido.criado_em.desc())
    )
    return [
        PedidoResumo(
            pedido_id=p.id,
            status=p.status.value,
            valor_total=p.valor_total,
            canal=p.canal.value,
            criado_em=p.criado_em,
        )
        for p in pedidos
    ]


@router.post("/{cliente_id}/resgates", response_model=ResgateOut, status_code=status.HTTP_201_CREATED)
def resgatar_pontos(
    cliente_id: uuid.UUID,
    payload: ResgateIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ResgateOut:
    exigir_self_ou_admin(cliente_id, usuario)
    cliente = user_service.obter_cliente(db, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    try:
        resgate = loyalty_service.resgatar_pontos(db, cliente, payload.pontos)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(resgate)
    return ResgateOut(
        resgate_id=resgate.id,
        pontos=resgate.pontos,
        cupom=resgate.cupom,
        saldo_restante=cliente.pontos_fidelidade,
    )
