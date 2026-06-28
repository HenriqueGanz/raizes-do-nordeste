from __future__ import annotations


def test_criar_pedido_fica_aguardando_pagamento(client, seed):
    payload = {
        "unidade_id": str(seed["unidade_id"]),
        "canal": "TOTEM",
        "metodo_pagamento": "PIX",
        "itens": [
            {"produto_id": str(seed["tapioca_id"]), "quantidade": 2},
            {"produto_id": str(seed["canjica_id"]), "quantidade": 1},
        ],
    }
    resp = client.post("/v1/pedidos", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert float(body["valor_total"]) == 47.30
    assert body["status"] == "AGUARDANDO_PAGAMENTO"
    assert body["pagamento"]["status"] == "PENDENTE"
    assert body["pagamento"]["idempotency_key"] is not None


def test_webhook_aprovado_confirma_pedido_criado_pela_api(client, seed, pagar):
    payload = {
        "unidade_id": str(seed["unidade_id"]),
        "canal": "TOTEM",
        "metodo_pagamento": "PIX",
        "itens": [{"produto_id": str(seed["tapioca_id"]), "quantidade": 1}],
    }
    pedido_id = client.post("/v1/pedidos", json=payload).json()["pedido_id"]

    resultado = pagar(pedido_id, "APROVADO")
    assert resultado["novo_status"] == "PAGO"

    pedido = client.get(f"/v1/pedidos/{pedido_id}").json()
    assert pedido["status"] == "PAGO"
    assert pedido["pagamento"]["status"] == "PAGO"


def test_criar_pedido_produto_indisponivel_retorna_422(client, seed):
    payload = {
        "unidade_id": str(seed["unidade_id"]),
        "canal": "BALCAO",
        "metodo_pagamento": "PIX",
        "itens": [{"produto_id": str(seed["produto_inexistente"]), "quantidade": 1}],
    }
    resp = client.post("/v1/pedidos", json=payload)
    assert resp.status_code == 422


def test_obter_pedido_apos_criacao(client, seed):
    payload = {
        "unidade_id": str(seed["unidade_id"]),
        "canal": "BALCAO",
        "metodo_pagamento": "PIX",
        "itens": [{"produto_id": str(seed["tapioca_id"]), "quantidade": 1}],
    }
    criado = client.post("/v1/pedidos", json=payload).json()
    resp = client.get(f"/v1/pedidos/{criado['pedido_id']}")
    assert resp.status_code == 200
    assert resp.json()["pedido_id"] == criado["pedido_id"]


def test_pedido_app_sem_autenticacao_e_negado(client, seed):
    payload = {
        "unidade_id": str(seed["unidade_id"]),
        "canal": "APP",
        "metodo_pagamento": "PIX",
        "itens": [{"produto_id": str(seed["tapioca_id"]), "quantidade": 1}],
    }
    resp = client.post("/v1/pedidos", json=payload)
    assert resp.status_code == 401


def test_pedido_app_autenticado_vincula_ao_cliente_do_token(client, seed, auth):
    payload = {
        "unidade_id": str(seed["unidade_id"]),
        "canal": "APP",
        "metodo_pagamento": "PIX",
        "itens": [{"produto_id": str(seed["tapioca_id"]), "quantidade": 1}],
    }
    resp = client.post("/v1/pedidos", json=payload, headers=auth("CLIENTE"))
    assert resp.status_code == 201
    pedido_id = resp.json()["pedido_id"]

    # O pedido deve aparecer no histórico do cliente do token, sem ele ter
    # sido informado em nenhum campo.
    historico = client.get(f"/v1/clientes/{seed['cliente_id']}/pedidos", headers=auth("CLIENTE")).json()
    assert any(p["pedido_id"] == pedido_id for p in historico)


def test_pedido_app_nao_aceita_cpf(client, seed, auth):
    payload = {
        "unidade_id": str(seed["unidade_id"]),
        "cpf": "12345678900",
        "canal": "APP",
        "metodo_pagamento": "PIX",
        "itens": [{"produto_id": str(seed["tapioca_id"]), "quantidade": 1}],
    }
    resp = client.post("/v1/pedidos", json=payload, headers=auth("CLIENTE"))
    assert resp.status_code == 422
