from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal

import pytest

from app.core.config import settings
from app.models.order import (
    CanalPedido,
    Pagamento,
    Pedido,
    StatusPagamento,
    StatusPedido,
)


def _assinar(corpo: bytes) -> str:
    return hmac.new(settings.payment_webhook_secret.encode(), corpo, hashlib.sha256).hexdigest()


@pytest.fixture()
def pedido_pendente(db_session, seed):
    pedido = Pedido(
        unidade_id=seed["unidade_id"],
        canal=CanalPedido.APP,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        valor_total=Decimal("18.90"),
    )
    pedido.pagamento = Pagamento(
        metodo="CARTAO_CREDITO",
        valor=Decimal("18.90"),
        status=StatusPagamento.PENDENTE,
        idempotency_key="pay_teste_001",
    )
    db_session.add(pedido)
    db_session.commit()
    db_session.refresh(pedido)
    return pedido


def test_webhook_aprovado_transiciona_para_pago(client, pedido_pendente):
    corpo = json.dumps(
        {
            "idempotency_key": "evt_1",
            "id_transacao_externa": "tx_ext_99",
            "pedido_id": str(pedido_pendente.id),
            "status": "APROVADO",
        }
    ).encode()
    resp = client.post("/v1/webhooks/pagamento", content=corpo, headers={"X-Signature": _assinar(corpo)})
    assert resp.status_code == 200
    assert resp.json()["novo_status"] == "PAGO"


def test_webhook_idempotente_nao_duplica(client, pedido_pendente):
    corpo = json.dumps(
        {"id_transacao_externa": "tx_ext_99", "pedido_id": str(pedido_pendente.id), "status": "APROVADO"}
    ).encode()
    sig = _assinar(corpo)
    r1 = client.post("/v1/webhooks/pagamento", content=corpo, headers={"X-Signature": sig})
    r2 = client.post("/v1/webhooks/pagamento", content=corpo, headers={"X-Signature": sig})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r2.json()["novo_status"] == "PAGO"


def test_webhook_assinatura_invalida_401(client, pedido_pendente):
    corpo = json.dumps(
        {"id_transacao_externa": "tx", "pedido_id": str(pedido_pendente.id), "status": "APROVADO"}
    ).encode()
    resp = client.post("/v1/webhooks/pagamento", content=corpo, headers={"X-Signature": "assinatura-errada"})
    assert resp.status_code == 401


def test_webhook_recusado_transiciona_para_recusado(client, pedido_pendente):
    corpo = json.dumps(
        {"id_transacao_externa": "tx_ext_x", "pedido_id": str(pedido_pendente.id), "status": "RECUSADO"}
    ).encode()
    resp = client.post("/v1/webhooks/pagamento", content=corpo, headers={"X-Signature": _assinar(corpo)})
    assert resp.status_code == 200
    assert resp.json()["novo_status"] == "PAGAMENTO_RECUSADO"
