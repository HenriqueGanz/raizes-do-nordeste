from __future__ import annotations

import uuid


def test_registrar_consentimento(client, seed, auth):
    resp = client.post(
        f"/v1/clientes/{seed['cliente_id']}/consentimentos",
        json={"finalidade": "MARKETING_SEGMENTADO", "base_legal": "CONSENTIMENTO", "concedido": True},
        headers=auth("CLIENTE"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "CONCEDIDO"
    assert body["finalidade"] == "MARKETING_SEGMENTADO"


def test_revogar_consentimento(client, seed, auth):
    criado = client.post(
        f"/v1/clientes/{seed['cliente_id']}/consentimentos",
        json={"finalidade": "MARKETING_SEGMENTADO", "base_legal": "CONSENTIMENTO", "concedido": True},
        headers=auth("CLIENTE"),
    ).json()
    resp = client.delete(
        f"/v1/clientes/{seed['cliente_id']}/consentimentos/{criado['consentimento_id']}",
        headers=auth("CLIENTE"),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REVOGADO"
    assert resp.json()["revogado_em"] is not None


def test_consentimento_exige_autenticacao(client, seed):
    resp = client.post(
        f"/v1/clientes/{seed['cliente_id']}/consentimentos",
        json={"finalidade": "MARKETING_SEGMENTADO"},
    )
    assert resp.status_code == 401


def test_consentimento_cliente_inexistente_404(client, seed, auth):
    resp = client.post(
        f"/v1/clientes/{uuid.uuid4()}/consentimentos",
        json={"finalidade": "MARKETING_SEGMENTADO"},
        headers=auth("ADMIN"),
    )
    assert resp.status_code == 404


def test_anonimizacao_remove_pii(db_session, seed):
    from app.models.user import Usuario

    cliente = db_session.get(Usuario, seed["cliente_id"])
    cliente.anonimizar()
    db_session.commit()
    db_session.refresh(cliente)

    assert cliente.anonimizado is True
    assert cliente.nome is None
    assert cliente.email is None
    assert cliente.anonymized_at is not None
