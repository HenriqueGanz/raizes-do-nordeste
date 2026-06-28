from __future__ import annotations


def test_cadastro_publico_de_cliente(client, seed):
    resp = client.post(
        "/v1/clientes",
        json={"nome": "Novo", "email": "novo@example.com", "senha": "segredo1", "cpf": "98765432100"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["papel"] == "CLIENTE"
    assert body["cpf"] == "98765432100"


def test_cliente_so_acessa_proprios_dados(client, seed, auth):
    resp = client.get(f"/v1/clientes/{seed['admin_id']}", headers=auth("CLIENTE"))
    assert resp.status_code == 403


def test_cliente_le_proprios_dados(client, seed, auth):
    resp = client.get(f"/v1/clientes/{seed['cliente_id']}", headers=auth("CLIENTE"))
    assert resp.status_code == 200
    assert str(resp.json()["cliente_id"]) == str(seed["cliente_id"])


def test_anonimizacao_lgpd(client, seed, auth):
    resp = client.delete(f"/v1/clientes/{seed['cliente_id']}", headers=auth("CLIENTE"))
    assert resp.status_code == 200
    assert resp.json()["anonimizado"] is True

    cliente = client.get(f"/v1/clientes/{seed['cliente_id']}", headers=auth("ADMIN")).json()
    assert cliente["nome"] is None
    assert cliente["cpf"] is None
