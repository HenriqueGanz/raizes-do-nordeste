from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import DisponibilidadeProduto, Produto, Unidade


@dataclass(frozen=True)
class ItemCardapio:
    produto_id: uuid.UUID
    nome: str
    categoria: str
    preco: Decimal
    sazonal: bool
    disponivel: bool


def _filtro_vigencia(stmt, referencia: date):
    """regra de vigencia sazonal"""
    return stmt.where(
        DisponibilidadeProduto.disponivel.is_(True),
        (DisponibilidadeProduto.inicio_vigencia.is_(None))
        | (DisponibilidadeProduto.inicio_vigencia <= referencia),
        (DisponibilidadeProduto.fim_vigencia.is_(None))
        | (DisponibilidadeProduto.fim_vigencia >= referencia),
    )


def listar_unidades(db: Session) -> list[Unidade]:
    return list(db.scalars(select(Unidade).where(Unidade.ativa.is_(True)).order_by(Unidade.nome)))


def obter_unidade(db: Session, unidade_id: uuid.UUID) -> Unidade | None:
    return db.scalar(select(Unidade).where(Unidade.id == unidade_id, Unidade.ativa.is_(True)))


def listar_cardapio(
    db: Session,
    unidade_id: uuid.UUID,
    referencia: date,
    categoria: str | None = None,
) -> list[ItemCardapio]:
    """retorna os itens da unidade na data de referencia"""
    stmt = (
        select(DisponibilidadeProduto, Produto)
        .join(Produto, Produto.id == DisponibilidadeProduto.produto_id)
        .where(DisponibilidadeProduto.unidade_id == unidade_id)
    )
    stmt = _filtro_vigencia(stmt, referencia)
    if categoria:
        stmt = stmt.where(Produto.categoria == categoria)

    itens: list[ItemCardapio] = []
    for disp, produto in db.execute(stmt).all():
        preco = disp.preco_local if disp.preco_local is not None else produto.preco_base
        itens.append(
            ItemCardapio(
                produto_id=produto.id,
                nome=produto.nome,
                categoria=produto.categoria,
                preco=Decimal(preco),
                sazonal=produto.sazonal,
                disponivel=True,
            )
        )
    return itens


def preco_disponivel(
    db: Session,
    unidade_id: uuid.UUID,
    produto_id: uuid.UUID,
    referencia: date,
) -> Decimal | None:
    stmt = (
        select(DisponibilidadeProduto, Produto)
        .join(Produto, Produto.id == DisponibilidadeProduto.produto_id)
        .where(
            DisponibilidadeProduto.unidade_id == unidade_id,
            DisponibilidadeProduto.produto_id == produto_id,
        )
    )
    stmt = _filtro_vigencia(stmt, referencia)
    row = db.execute(stmt).first()
    if row is None:
        return None
    disp, produto = row
    if disp.quantidade_estoque is not None and disp.quantidade_estoque <= 0:
        return None  # sem estoque unidade
    return Decimal(disp.preco_local if disp.preco_local is not None else produto.preco_base)


def criar_produto(db: Session, dados: "ProdutoCreate") -> Produto:
    produto = Produto(
        nome=dados.nome,
        preco_base=dados.preco_base,
        categoria=dados.categoria,
        sazonal=dados.sazonal,
    )
    db.add(produto)
    db.flush()
    return produto


def atualizar_produto(db: Session, produto_id: uuid.UUID, dados: "ProdutoUpdate") -> Produto | None:
    produto = db.get(Produto, produto_id)
    if produto is None:
        return None
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(produto, campo, valor)
    db.flush()
    return produto


def remover_produto(db: Session, produto_id: uuid.UUID) -> bool:
    produto = db.get(Produto, produto_id)
    if produto is None:
        return False
    db.delete(produto)
    return True


def definir_disponibilidade(
    db: Session,
    unidade_id: uuid.UUID,
    produto_id: uuid.UUID,
    dados: "DisponibilidadeIn",
) -> DisponibilidadeProduto:
    """cria ou atualiza a disponibilidade do produto"""
    disp = db.scalar(
        select(DisponibilidadeProduto).where(
            DisponibilidadeProduto.unidade_id == unidade_id,
            DisponibilidadeProduto.produto_id == produto_id,
        )
    )
    if disp is None:
        disp = DisponibilidadeProduto(unidade_id=unidade_id, produto_id=produto_id)
        db.add(disp)
    disp.preco_local = dados.preco_local
    disp.disponivel = dados.disponivel
    disp.quantidade_estoque = dados.quantidade_estoque
    disp.inicio_vigencia = dados.inicio_vigencia
    disp.fim_vigencia = dados.fim_vigencia
    db.flush()
    return disp


def remover_disponibilidade(db: Session, unidade_id: uuid.UUID, produto_id: uuid.UUID) -> bool:
    disp = db.scalar(
        select(DisponibilidadeProduto).where(
            DisponibilidadeProduto.unidade_id == unidade_id,
            DisponibilidadeProduto.produto_id == produto_id,
        )
    )
    if disp is None:
        return False
    db.delete(disp)
    return True


def baixar_estoque(db: Session, unidade_id: uuid.UUID, produto_id: uuid.UUID, qtd: int) -> None:
    """decrementa o estoque local quando tem controle de quantidade"""
    disp = db.scalar(
        select(DisponibilidadeProduto).where(
            DisponibilidadeProduto.unidade_id == unidade_id,
            DisponibilidadeProduto.produto_id == produto_id,
        )
    )
    if disp is not None and disp.quantidade_estoque is not None:
        disp.quantidade_estoque = max(0, disp.quantidade_estoque - qtd)


def criar_unidade(db: Session, dados: "UnidadeCreate") -> Unidade:
    unidade = Unidade(
        nome=dados.nome,
        regiao=dados.regiao,
        cidade=dados.cidade,
        formato_operacao=dados.formato_operacao,
        ativa=dados.ativa,
    )
    db.add(unidade)
    db.flush()
    return unidade


def atualizar_unidade(db: Session, unidade_id: uuid.UUID, dados: "UnidadeUpdate") -> Unidade | None:
    unidade = db.get(Unidade, unidade_id)
    if unidade is None:
        return None
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(unidade, campo, valor)
    db.flush()
    return unidade
