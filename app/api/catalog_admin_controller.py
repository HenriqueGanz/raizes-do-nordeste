from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_papel
from app.core.database import get_db
from app.models.catalog import AuditLog, Produto, Unidade
from app.models.user import Usuario
from app.schemas.catalog import (
    DisponibilidadeIn,
    ProdutoCreate,
    ProdutoOut,
    ProdutoUpdate,
    UnidadeCreate,
    UnidadeUpdate,
)
from app.services import catalog_service

router = APIRouter(prefix="/v1", tags=["catalogo-admin"])

_admin = require_papel("ADMIN")


def _to_out(produto: Produto) -> ProdutoOut:
    return ProdutoOut(
        produto_id=produto.id,
        nome=produto.nome,
        preco_base=produto.preco_base,
        categoria=produto.categoria,
        sazonal=produto.sazonal,
    )


def _auditar(db: Session, ator: Usuario, acao: str, entidade: str, detalhes: dict) -> None:
    db.add(AuditLog(ator_id=ator.id, acao=acao, entidade=entidade, detalhes=detalhes))


@router.post("/produtos", response_model=ProdutoOut, status_code=status.HTTP_201_CREATED)
def criar_produto(
    payload: ProdutoCreate, db: Session = Depends(get_db), admin: Usuario = Depends(_admin)
) -> ProdutoOut:
    produto = catalog_service.criar_produto(db, payload)
    _auditar(db, admin, "CRIAR_PRODUTO", "produto", {"nome": produto.nome})
    db.commit()
    db.refresh(produto)
    return _to_out(produto)


@router.get("/produtos", response_model=list[ProdutoOut])
def listar_produtos(db: Session = Depends(get_db), admin: Usuario = Depends(_admin)) -> list[ProdutoOut]:
    return [_to_out(p) for p in db.scalars(select(Produto).order_by(Produto.nome))]


@router.get("/produtos/{produto_id}", response_model=ProdutoOut)
def obter_produto(
    produto_id: uuid.UUID, db: Session = Depends(get_db), admin: Usuario = Depends(_admin)
) -> ProdutoOut:
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return _to_out(produto)


@router.put("/produtos/{produto_id}", response_model=ProdutoOut)
def atualizar_produto(
    produto_id: uuid.UUID,
    payload: ProdutoUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(_admin),
) -> ProdutoOut:
    produto = catalog_service.atualizar_produto(db, produto_id, payload)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    _auditar(db, admin, "ATUALIZAR_PRODUTO", "produto", {"produto_id": str(produto_id)})
    db.commit()
    db.refresh(produto)
    return _to_out(produto)


@router.delete("/produtos/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_produto(
    produto_id: uuid.UUID, db: Session = Depends(get_db), admin: Usuario = Depends(_admin)
) -> None:
    if not catalog_service.remover_produto(db, produto_id):
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    _auditar(db, admin, "REMOVER_PRODUTO", "produto", {"produto_id": str(produto_id)})
    db.commit()


@router.post("/unidades", status_code=status.HTTP_201_CREATED)
def criar_unidade(
    payload: UnidadeCreate, db: Session = Depends(get_db), admin: Usuario = Depends(_admin)
) -> dict:
    unidade = catalog_service.criar_unidade(db, payload)
    _auditar(db, admin, "CRIAR_UNIDADE", "unidade", {"nome": unidade.nome})
    db.commit()
    db.refresh(unidade)
    return {"unidade_id": str(unidade.id), "nome": unidade.nome, "cidade": unidade.cidade}


@router.put("/unidades/{unidade_id}")
def atualizar_unidade(
    unidade_id: uuid.UUID,
    payload: UnidadeUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(_admin),
) -> dict:
    unidade = catalog_service.atualizar_unidade(db, unidade_id, payload)
    if unidade is None:
        raise HTTPException(status_code=404, detail="Unidade não encontrada.")
    _auditar(db, admin, "ATUALIZAR_UNIDADE", "unidade", {"unidade_id": str(unidade_id)})
    db.commit()
    return {"unidade_id": str(unidade.id), "nome": unidade.nome, "ativa": unidade.ativa}


@router.put("/unidades/{unidade_id}/cardapio/{produto_id}")
def definir_disponibilidade(
    unidade_id: uuid.UUID,
    produto_id: uuid.UUID,
    payload: DisponibilidadeIn,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(_admin),
) -> dict:
    if db.get(Unidade, unidade_id) is None:
        raise HTTPException(status_code=404, detail="Unidade não encontrada.")
    if db.get(Produto, produto_id) is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    disp = catalog_service.definir_disponibilidade(db, unidade_id, produto_id, payload)
    _auditar(
        db, admin, "DEFINIR_DISPONIBILIDADE", "disponibilidade_produto",
        {"unidade_id": str(unidade_id), "produto_id": str(produto_id), "disponivel": disp.disponivel},
    )
    db.commit()
    return {
        "unidade_id": str(unidade_id),
        "produto_id": str(produto_id),
        "disponivel": disp.disponivel,
        "preco_local": float(disp.preco_local) if disp.preco_local is not None else None,
        "quantidade_estoque": disp.quantidade_estoque,
    }


@router.delete(
    "/unidades/{unidade_id}/cardapio/{produto_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remover_disponibilidade(
    unidade_id: uuid.UUID,
    produto_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(_admin),
) -> None:
    if not catalog_service.remover_disponibilidade(db, unidade_id, produto_id):
        raise HTTPException(status_code=404, detail="Item não está no cardápio da unidade.")
    _auditar(
        db, admin, "REMOVER_DISPONIBILIDADE", "disponibilidade_produto",
        {"unidade_id": str(unidade_id), "produto_id": str(produto_id)},
    )
    db.commit()
