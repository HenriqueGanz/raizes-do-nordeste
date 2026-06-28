from __future__ import annotations


def test_criar_produto_como_admin(client, seed, auth):
    resp = client.post(
        "/v1/produtos",
        json={"nome": "Bolo de rolo", "preco_base": "12.00", "categoria": "doce"},
        headers=auth("ADMIN"),
    )
    assert resp.status_code == 201
    assert resp.json()["nome"] == "Bolo de rolo"

    listagem = client.get("/v1/produtos", headers=auth("ADMIN")).json()
    assert any(p["nome"] == "Bolo de rolo" for p in listagem)


def test_criar_produto_sem_papel_admin_403(client, seed, auth):
    resp = client.post(
        "/v1/produtos",
        json={"nome": "X", "preco_base": "1.00", "categoria": "y"},
        headers=auth("CLIENTE"),
    )
    assert resp.status_code == 403


def test_publicar_produto_no_cardapio_da_unidade(client, seed, auth):
    produto = client.post(
        "/v1/produtos",
        json={"nome": "Cuscuz", "preco_base": "8.00", "categoria": "salgado"},
        headers=auth("ADMIN"),
    ).json()

    resp = client.put(
        f"/v1/unidades/{seed['unidade_id']}/cardapio/{produto['produto_id']}",
        json={"preco_local": "7.50", "disponivel": True, "quantidade_estoque": 10},
        headers=auth("ADMIN"),
    )
    assert resp.status_code == 200

    cardapio = client.get(f"/v1/unidades/{seed['unidade_id']}/cardapio").json()
    nomes = {i["nome"] for i in cardapio["itens"]}
    assert "Cuscuz" in nomes


def test_remover_produto(client, seed, auth):
    produto = client.post(
        "/v1/produtos",
        json={"nome": "Temporario", "preco_base": "5.00", "categoria": "z"},
        headers=auth("ADMIN"),
    ).json()
    resp = client.delete(f"/v1/produtos/{produto['produto_id']}", headers=auth("ADMIN"))
    assert resp.status_code == 204
