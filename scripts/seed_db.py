"""Popula o banco com dados com mocks
  # com docker-compose:
  docker-compose exec api python scripts/seed_db.py

  # Local com venv ativado:
  DATABASE_URL=postgresql+psycopg://raizes:raizes@localhost:5433/raizes python scripts/seed_db.py
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import date

import psycopg

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.core.security import hash_senha


def main() -> None:
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        raise RuntimeError("DATABASE_URL não definida")

    url = raw_url.replace("postgresql+psycopg://", "postgresql://")

    unidade_id = str(uuid.uuid4())
    tapioca_id = str(uuid.uuid4())
    canjica_id = str(uuid.uuid4())
    usuario_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())
    operador_id = str(uuid.uuid4())

    cliente_senha = "cliente123"
    operador_senha = "operador123"

    with psycopg.connect(url) as conn:
        conn.execute(
            """
            INSERT INTO unidade (id, nome, regiao, cidade, formato_operacao, ativa)
            VALUES (%s, %s, %s, %s, 'COMPLETA', TRUE)
            """,
            (unidade_id, "Raízes - Recife Boa Viagem", "Nordeste", "Recife"),
        )

        conn.execute(
            "INSERT INTO produto (id, nome, preco_base, categoria, sazonal) VALUES (%s,%s,%s,%s,%s)",
            (tapioca_id, "Tapioca de carne de sol com queijo coalho", 18.90, "tapioca", False),
        )
        conn.execute(
            "INSERT INTO produto (id, nome, preco_base, categoria, sazonal) VALUES (%s,%s,%s,%s,%s)",
            (canjica_id, "Canjica junina", 9.50, "doce", True),
        )

        conn.execute(
            """
            INSERT INTO disponibilidade_produto (unidade_id, produto_id, preco_local, disponivel)
            VALUES (%s, %s, %s, TRUE)
            """,
            (unidade_id, tapioca_id, 18.90),
        )

        conn.execute(
            """
            INSERT INTO disponibilidade_produto
                (unidade_id, produto_id, preco_local, disponivel, inicio_vigencia, fim_vigencia)
            VALUES (%s, %s, %s, TRUE, %s, %s)
            """,
            (unidade_id, canjica_id, 9.50, date(2026, 6, 1), date(2026, 7, 31)),
        )

        conn.execute(
            """
            INSERT INTO usuario (id, nome, email, cpf, papel, senha_hash)
            VALUES (%s, %s, %s, %s, 'CLIENTE', %s)
            """,
            (usuario_id, "Cliente Demo", "demo@raizesdonordeste.com.br", "12345678900",
             hash_senha(cliente_senha)),
        )
        conn.execute(
            """
            INSERT INTO consentimento (usuario_id, finalidade, base_legal, status)
            VALUES (%s, 'FIDELIDADE', 'CONSENTIMENTO', 'CONCEDIDO')
            """,
            (usuario_id,),
        )

        conn.execute(
            "INSERT INTO usuario (id, nome, email, papel, senha_hash) VALUES (%s,%s,%s,'ADMIN',%s)",
            (admin_id, "Admin Matriz", settings.admin_seed_email, hash_senha(settings.admin_seed_senha)),
        )
        conn.execute(
            "INSERT INTO usuario (id, nome, email, papel, senha_hash) VALUES (%s,%s,%s,'OPERADOR',%s)",
            (operador_id, "Operador Cozinha", "operador@raizesdonordeste.com.br",
             hash_senha(operador_senha)),
        )

        conn.commit()

    print("=" * 60)
    print("[seed_db] Dados inseridos com sucesso!")
    print(f"  UNIDADE_ID  = {unidade_id}")
    print(f"  TAPIOCA_ID  = {tapioca_id}")
    print(f"  CANJICA_ID  = {canjica_id}")
    print(f"  USUARIO_ID  = {usuario_id}")
    print("-" * 60)
    print("  CREDENCIAIS (POST /v1/auth/login):")
    print(f"    ADMIN    -> {settings.admin_seed_email} / {settings.admin_seed_senha}")
    print(f"    OPERADOR -> operador@raizesdonordeste.com.br / {operador_senha}")
    print(f"    CLIENTE  -> demo@raizesdonordeste.com.br / {cliente_senha}  (CPF 12345678900)")
    print("=" * 60)


if __name__ == "__main__":
    main()
