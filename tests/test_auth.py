from __future__ import annotations


def test_login_admin_ok(client, seed):
    resp = client.post("/v1/auth/login", json={"email": "admin@example.com", "senha": "admin123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["papel"] == "ADMIN"
    assert body["access_token"]


def test_login_senha_errada_401(client, seed):
    resp = client.post("/v1/auth/login", json={"email": "admin@example.com", "senha": "errada"})
    assert resp.status_code == 401


def test_rota_protegida_sem_token_401(client, seed):
    resp = client.get("/v1/produtos")
    assert resp.status_code == 401
