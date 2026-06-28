from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import criar_token, hash_senha
from app.main import app
from app.models.catalog import DisponibilidadeProduto, Produto, Unidade
from app.models.user import Consentimento, PapelUsuario, Usuario


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seed(db_session):
    unidade = Unidade(nome="Recife Boa Viagem", regiao="Nordeste", cidade="Recife")
    tapioca = Produto(nome="Tapioca de carne de sol", preco_base=Decimal("18.90"), categoria="tapioca")
    canjica = Produto(nome="Canjica junina", preco_base=Decimal("9.50"), categoria="doce", sazonal=True)
    cliente = Usuario(
        nome="Dona Francisca", email="francisca@example.com", cpf="12345678900",
        papel=PapelUsuario.CLIENTE, senha_hash=hash_senha("cliente123"),
    )
    admin = Usuario(
        nome="Admin", email="admin@example.com", papel=PapelUsuario.ADMIN,
        senha_hash=hash_senha("admin123"),
    )
    operador = Usuario(
        nome="Operador", email="operador@example.com", papel=PapelUsuario.OPERADOR,
        senha_hash=hash_senha("operador123"),
    )
    db_session.add_all([unidade, tapioca, canjica, cliente, admin, operador])
    db_session.flush()

    db_session.add(
        Consentimento(usuario_id=cliente.id, finalidade="FIDELIDADE", base_legal="CONSENTIMENTO")
    )

    hoje = date.today()
    db_session.add(
        DisponibilidadeProduto(unidade_id=unidade.id, produto_id=tapioca.id, disponivel=True)
    )
    db_session.add(
        DisponibilidadeProduto(
            unidade_id=unidade.id,
            produto_id=canjica.id,
            disponivel=True,
            inicio_vigencia=hoje - timedelta(days=5),
            fim_vigencia=hoje + timedelta(days=5),
        )
    )
    db_session.commit()

    return {
        "unidade_id": unidade.id,
        "tapioca_id": tapioca.id,
        "canjica_id": canjica.id,
        "cliente_id": cliente.id,
        "admin_id": admin.id,
        "operador_id": operador.id,
        "produto_inexistente": uuid.uuid4(),
    }


@pytest.fixture()
def auth(seed):
    """Gera headers Authorization para um papel/usuário semeado."""
    def _headers(papel: str = "ADMIN", usuario_id=None) -> dict[str, str]:
        uid = usuario_id or seed[f"{papel.lower()}_id"]
        return {"Authorization": f"Bearer {criar_token(str(uid), papel)}"}

    return _headers


@pytest.fixture()
def pagar(client):
    """Simula o gateway confirmando o pagamento via webhook (APROVADO ou RECUSADO)."""
    def _pagar(pedido_id, resultado: str = "APROVADO") -> dict:
        corpo = json.dumps(
            {
                "idempotency_key": f"evt_{uuid.uuid4().hex[:10]}",
                "id_transacao_externa": f"tx_{uuid.uuid4().hex[:10]}",
                "pedido_id": str(pedido_id),
                "status": resultado,
            }
        ).encode()
        assinatura = hmac.new(
            settings.payment_webhook_secret.encode(), corpo, hashlib.sha256
        ).hexdigest()
        resp = client.post(
            "/v1/webhooks/pagamento", content=corpo, headers={"X-Signature": assinatura}
        )
        return resp.json()

    return _pagar
