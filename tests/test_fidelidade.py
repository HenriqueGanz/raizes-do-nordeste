from __future__ import annotations


def _pedido_pago_com_cpf(client, pagar, seed, cpf: str) -> str:
    resp = client.post(
        "/v1/pedidos",
        json={
            "unidade_id": str(seed["unidade_id"]),
            "cpf": cpf,
            "canal": "TOTEM",
            "metodo_pagamento": "PIX",
            "itens": [{"produto_id": str(seed["tapioca_id"]), "quantidade": 1}],
        },
    )
    pedido_id = resp.json()["pedido_id"]
    pagar(pedido_id, "APROVADO")
    return pedido_id


def test_acumula_pontos_com_consentimento(client, seed, auth, pagar):
    _pedido_pago_com_cpf(client, pagar, seed, "12345678900")
    cliente = client.get(f"/v1/clientes/{seed['cliente_id']}", headers=auth("ADMIN")).json()
    assert cliente["pontos_fidelidade"] == 18


def test_nao_acumula_sem_consentimento(client, seed, auth, pagar):
    novo = client.post(
        "/v1/clientes",
        json={"nome": "Sem Consent", "email": "sc@example.com", "senha": "segredo1", "cpf": "11122233344"},
    ).json()
    _pedido_pago_com_cpf(client, pagar, seed, "11122233344")
    atual = client.get(f"/v1/clientes/{novo['cliente_id']}", headers=auth("ADMIN")).json()
    assert atual["pontos_fidelidade"] == 0


def test_resgate_de_pontos(client, seed, auth, pagar):
    _pedido_pago_com_cpf(client, pagar, seed, "12345678900")  # 18 pontos
    resp = client.post(
        f"/v1/clientes/{seed['cliente_id']}/resgates",
        json={"pontos": 10},
        headers=auth("CLIENTE"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["saldo_restante"] == 8
    assert body["cupom"].startswith("RAIZ-")


def test_resgate_saldo_insuficiente_409(client, seed, auth):
    resp = client.post(
        f"/v1/clientes/{seed['cliente_id']}/resgates",
        json={"pontos": 9999},
        headers=auth("CLIENTE"),
    )
    assert resp.status_code == 409
