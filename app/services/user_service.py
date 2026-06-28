from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_senha
from app.models.user import PapelUsuario, Usuario


def obter_cliente(db: Session, cliente_id: uuid.UUID) -> Usuario | None:
    return db.get(Usuario, cliente_id)


def buscar_por_cpf(db: Session, cpf: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.cpf == cpf))


def criar_cliente(db: Session, dados: "ClienteCreate") -> Usuario:
    cliente = Usuario(
        nome=dados.nome,
        email=dados.email,
        cpf=dados.cpf,
        data_nascimento=dados.data_nascimento,
        senha_hash=hash_senha(dados.senha),
        papel=PapelUsuario.CLIENTE,
    )
    db.add(cliente)
    db.flush()
    return cliente


def atualizar_cliente(db: Session, cliente: Usuario, dados: "ClienteUpdate") -> Usuario:
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    db.flush()
    return cliente


def find_or_create_por_cpf(db: Session, cpf: str) -> Usuario:
    """vincula o cliente do CPF informado e se não existir cria um cadastro simples"""
    cliente = buscar_por_cpf(db, cpf)
    if cliente is None:
        cliente = Usuario(cpf=cpf, papel=PapelUsuario.CLIENTE)
        db.add(cliente)
        db.flush()
    return cliente
