from __future__ import annotations


def test_listar_unidades(client, seed):
    resp = client.get("/v1/unidades")
    assert resp.status_code == 200
    ids = {u["unidade_id"] for u in resp.json()}
    assert str(seed["unidade_id"]) in ids


def test_cardapio_lista_itens_disponiveis(client, seed):
    resp = client.get(f"/v1/unidades/{seed['unidade_id']}/cardapio")
    assert resp.status_code == 200
    nomes = {i["nome"] for i in resp.json()["itens"]}
    assert "Tapioca de carne de sol" in nomes
    assert "Canjica junina" in nomes


def test_cardapio_filtra_por_categoria(client, seed):
    resp = client.get(f"/v1/unidades/{seed['unidade_id']}/cardapio", params={"categoria": "tapioca"})
    assert resp.status_code == 200
    categorias = {i["categoria"] for i in resp.json()["itens"]}
    assert categorias == {"tapioca"}


def test_cardapio_fora_da_vigencia_oculta_sazonal(client, seed):
    resp = client.get(
        f"/v1/unidades/{seed['unidade_id']}/cardapio", params={"data": "2099-12-31"}
    )
    assert resp.status_code == 200
    nomes = {i["nome"] for i in resp.json()["itens"]}
    assert "Canjica junina" not in nomes


def test_cardapio_unidade_inexistente(client, seed):
    import uuid

    resp = client.get(f"/v1/unidades/{uuid.uuid4()}/cardapio")
    assert resp.status_code == 404
