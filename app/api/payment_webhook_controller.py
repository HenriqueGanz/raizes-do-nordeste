from __future__ import annotations

import hashlib
import hmac
import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.catalog import AuditLog
from app.models.order import Pagamento, Pedido, StatusPagamento, StatusPedido
from app.services import loyalty_service

router = APIRouter(prefix="/v1", tags=["pagamentos"])


def _assinatura_valida(corpo: bytes, assinatura: str | None) -> bool:
    if not assinatura:
        return False
    esperada = hmac.new(
        settings.payment_webhook_secret.encode(), corpo, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(esperada, assinatura)


@router.post("/webhooks/pagamento")
async def webhook_pagamento(
    request: Request,
    x_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    corpo = await request.body()
    if not _assinatura_valida(corpo, x_signature):
        raise HTTPException(status_code=401, detail="Assinatura inválida.")

    evento = json.loads(corpo or b"{}")
    pedido_id = evento.get("pedido_id")
    resultado = evento.get("status")
    id_tx = evento.get("id_transacao_externa")

    pedido = db.get(Pedido, uuid.UUID(pedido_id))
    if pedido is None or pedido.pagamento is None:
        raise HTTPException(status_code=404, detail="Pedido/pagamento não encontrado.")

    pagamento: Pagamento = pedido.pagamento

    if resultado == "APROVADO" and pagamento.status == StatusPagamento.PAGO:
        return {"recebido": True, "pedido_id": pedido_id, "novo_status": pedido.status.value}
    if resultado == "RECUSADO" and pagamento.status == StatusPagamento.RECUSADO:
        return {"recebido": True, "pedido_id": pedido_id, "novo_status": pedido.status.value}

    try:
        if resultado == "APROVADO":
            pagamento.status = StatusPagamento.PAGO
            pagamento.id_transacao_externa = id_tx
            pedido.transicionar_para(StatusPedido.PAGO)
            loyalty_service.acumular_pontos(db, pedido)
        elif resultado == "RECUSADO":
            pagamento.status = StatusPagamento.RECUSADO
            pagamento.id_transacao_externa = id_tx
            pedido.transicionar_para(StatusPedido.PAGAMENTO_RECUSADO)
        else:
            raise HTTPException(status_code=422, detail="Status de pagamento inválido.")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.add(
        AuditLog(
            pedido_id=pedido.id,
            acao="WEBHOOK_PAGAMENTO",
            entidade="pagamento",
            detalhes={"resultado": resultado, "id_transacao_externa": id_tx},
        )
    )
    db.commit()
    db.refresh(pedido)
    return {"recebido": True, "pedido_id": pedido_id, "novo_status": pedido.status.value}
