from __future__ import annotations


def _criar_pedido_pago(client, pagar, seed) -> str:
    resp = client.post(
        "/v1/pedidos",
        json={
            "unidade_id": str(seed["unidade_id"]),
            "canal": "TOTEM",
            "metodo_pagamento": "PIX",
            "itens": [{"produto_id": str(seed["tapioca_id"]), "quantidade": 1}],
        },
    )
    pedido_id = resp.json()["pedido_id"]
    pagar(pedido_id, "APROVADO")
    return pedido_id


def test_fluxo_cozinha_completo(client, seed, auth, pagar):
    pedido_id = _criar_pedido_pago(client, pagar, seed)
    op = auth("OPERADOR")

    assert client.post(f"/v1/pedidos/{pedido_id}/aceitar", headers=op).json()["status"] == "EM_PREPARO"
    assert client.post(f"/v1/pedidos/{pedido_id}/pronto", headers=op).json()["status"] == "PRONTO"
    assert client.post(f"/v1/pedidos/{pedido_id}/entregar", headers=op).json()["status"] == "ENTREGUE"


def test_transicao_invalida_409(client, seed, auth, pagar):
    pedido_id = _criar_pedido_pago(client, pagar, seed)
    # Pular direto para PRONTO sem aceitar é invalido.
    resp = client.post(f"/v1/pedidos/{pedido_id}/pronto", headers=auth("OPERADOR"))
    assert resp.status_code == 409


def test_operacao_exige_papel(client, seed, auth, pagar):
    pedido_id = _criar_pedido_pago(client, pagar, seed)
    resp = client.post(f"/v1/pedidos/{pedido_id}/aceitar", headers=auth("CLIENTE"))
    assert resp.status_code == 403


def test_desconto_auditado(client, db_session, seed, auth):
    # Desconto só vale antes do pagamento, criamos um pedido AGUARDANDO_PAGAMENTO.
    from decimal import Decimal

    from app.models.order import CanalPedido, Pedido, StatusPedido

    pedido = Pedido(
        unidade_id=seed["unidade_id"],
        canal=CanalPedido.BALCAO,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        valor_total=Decimal("18.90"),
    )
    db_session.add(pedido)
    db_session.commit()
    db_session.refresh(pedido)

    resp = client.post(
        f"/v1/pedidos/{pedido.id}/desconto",
        json={"percentual": "10", "motivo": "cortesia"},
        headers=auth("ADMIN"),
    )
    assert resp.status_code == 200
    assert resp.json()["valor_total"] == 17.01
