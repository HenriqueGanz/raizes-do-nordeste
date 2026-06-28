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

_EXEMPLO_WEBHOOK = {
    "idempotency_key": "evt_8a7b9c2d1e",
    "id_transacao_externa": "tx_pix_523d249506",
    "pedido_id": "00000000-0000-0000-0000-000000000000",
    "status": "APROVADO",
}
_WEBHOOK_BODY_SCHEMA = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["idempotency_key", "id_transacao_externa", "pedido_id", "status"],
                    "properties": {
                        "idempotency_key": {"type": "string"},
                        "id_transacao_externa": {"type": "string"},
                        "pedido_id": {"type": "string", "format": "uuid"},
                        "status": {"type": "string", "enum": ["APROVADO", "RECUSADO"]},
                    },
                },
                "example": _EXEMPLO_WEBHOOK,
            }
        },
    }
}


def _assinatura_valida(corpo: bytes, assinatura: str | None) -> bool:
    if not assinatura:
        return False
    esperada = hmac.new(
        settings.payment_webhook_secret.encode(), corpo, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(esperada, assinatura)


@router.post(
    "/webhooks/pagamento/assinatura",
    summary="[Ferramenta de teste] Calcula o X-Signature de um corpo de webhook",
    openapi_extra=_WEBHOOK_BODY_SCHEMA,
)
async def calcular_assinatura(request: Request) -> dict:
    """Criado apenas para testar o webhook manualmente pelo
    Swagger, cole aqui o mesmo corpo que vai enviar para `/webhooks/pagamento` e
    use a assinatura devolvida no header `X-Signature` da chamada real. use o texto exatamente
    igual nas duas chamadas (qualquer espaço ou quebra de linha diferente gera outra assinatura)
    """
    corpo = await request.body()
    assinatura = hmac.new(settings.payment_webhook_secret.encode(), corpo, hashlib.sha256).hexdigest()
    return {"x_signature": assinatura}


@router.post("/webhooks/pagamento", openapi_extra=_WEBHOOK_BODY_SCHEMA)
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
