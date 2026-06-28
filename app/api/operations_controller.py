from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_papel
from app.core.database import get_db
from app.models.catalog import AuditLog
from app.models.order import Pedido, StatusPedido
from app.models.user import Usuario
from app.schemas.order import DescontoIn

router = APIRouter(prefix="/v1", tags=["operacao"])

_operacao = require_papel("OPERADOR", "ADMIN")

# status que os operadores da cozinha acompanham no painel
_FILA = (StatusPedido.PAGO, StatusPedido.EM_PREPARO, StatusPedido.PRONTO)


def _transicionar(db: Session, pedido_id: uuid.UUID, novo: StatusPedido, ator: Usuario) -> dict:
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    try:
        pedido.transicionar_para(novo)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if novo == StatusPedido.CANCELADO:
        db.add(
            AuditLog(
                ator_id=ator.id, pedido_id=pedido.id, acao="CANCELAR_PEDIDO", entidade="pedido",
                detalhes={"de": pedido.status.value},
            )
        )
    db.commit()
    db.refresh(pedido)
    return {"pedido_id": str(pedido.id), "status": pedido.status.value}


@router.post("/pedidos/{pedido_id}/aceitar")
def aceitar(pedido_id: uuid.UUID, db: Session = Depends(get_db), ator: Usuario = Depends(_operacao)) -> dict:
    return _transicionar(db, pedido_id, StatusPedido.EM_PREPARO, ator)


@router.post("/pedidos/{pedido_id}/pronto")
def marcar_pronto(pedido_id: uuid.UUID, db: Session = Depends(get_db), ator: Usuario = Depends(_operacao)) -> dict:
    return _transicionar(db, pedido_id, StatusPedido.PRONTO, ator)


@router.post("/pedidos/{pedido_id}/entregar")
def entregar(pedido_id: uuid.UUID, db: Session = Depends(get_db), ator: Usuario = Depends(_operacao)) -> dict:
    return _transicionar(db, pedido_id, StatusPedido.ENTREGUE, ator)


@router.post("/pedidos/{pedido_id}/cancelar")
def cancelar(pedido_id: uuid.UUID, db: Session = Depends(get_db), ator: Usuario = Depends(_operacao)) -> dict:
    return _transicionar(db, pedido_id, StatusPedido.CANCELADO, ator)


@router.post("/pedidos/{pedido_id}/desconto")
def aplicar_desconto(
    pedido_id: uuid.UUID,
    payload: DescontoIn,
    db: Session = Depends(get_db),
    ator: Usuario = Depends(_operacao),
) -> dict:
    """aplica o desconto antes do pagamento"""
    if (payload.percentual is None) == (payload.valor is None):
        raise HTTPException(status_code=422, detail="Informe apenas percentual OU valor.")

    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    if pedido.status not in (StatusPedido.CRIADO, StatusPedido.AGUARDANDO_PAGAMENTO):
        raise HTTPException(status_code=409, detail="Desconto só antes do pagamento.")

    total = Decimal(pedido.valor_total)
    abatimento = (total * payload.percentual / 100) if payload.percentual is not None else payload.valor
    novo_total = max(Decimal("0"), total - abatimento)
    pedido.valor_total = novo_total
    if pedido.pagamento is not None:
        pedido.pagamento.valor = novo_total

    db.add(
        AuditLog(
            ator_id=ator.id, pedido_id=pedido.id, acao="APLICAR_DESCONTO", entidade="pedido",
            detalhes={
                "de": float(total), "para": float(novo_total), "motivo": payload.motivo,
            },
        )
    )
    db.commit()
    db.refresh(pedido)
    return {"pedido_id": str(pedido.id), "valor_total": float(pedido.valor_total)}


@router.get("/unidades/{unidade_id}/fila")
def fila_cozinha(
    unidade_id: uuid.UUID, db: Session = Depends(get_db), ator: Usuario = Depends(_operacao)
) -> list[dict]:
    """painel da cozinha, retorna os pedidos pagos, em preparo ou prontos na unidade"""
    pedidos = db.scalars(
        select(Pedido)
        .where(Pedido.unidade_id == unidade_id, Pedido.status.in_(_FILA))
        .order_by(Pedido.criado_em)
    )
    return [
        {"pedido_id": str(p.id), "status": p.status.value, "valor_total": float(p.valor_total)}
        for p in pedidos
    ]
