from __future__ import annotations


def _criar_pedido_pago(client, pagar, seed):
    resp = client.post(
        "/v1/pedidos",
        json={
            "unidade_id": str(seed["unidade_id"]),
            "canal": "TOTEM",
            "metodo_pagamento": "PIX",
            "itens": [{"produto_id": str(seed["tapioca_id"]), "quantidade": 2}],
        },
    )
    pagar(resp.json()["pedido_id"], "APROVADO")


def test_relatorio_vendas_admin(client, seed, auth, pagar):
    _criar_pedido_pago(client, pagar, seed)
    resp = client.get("/v1/relatorios/vendas", headers=auth("ADMIN"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_faturamento"] > 0
    assert any(str(seed["unidade_id"]) == u["unidade_id"] for u in body["unidades"])


def test_relatorio_vendas_negado_para_cliente(client, seed, auth):
    resp = client.get("/v1/relatorios/vendas", headers=auth("CLIENTE"))
    assert resp.status_code == 403
