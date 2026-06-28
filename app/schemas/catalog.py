from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.catalog import FormatoOperacao


class ProdutoCreate(BaseModel):
    nome: str
    preco_base: Decimal = Field(ge=0)
    categoria: str
    sazonal: bool = False


class ProdutoUpdate(BaseModel):
    nome: str | None = None
    preco_base: Decimal | None = Field(default=None, ge=0)
    categoria: str | None = None
    sazonal: bool | None = None


class ProdutoOut(BaseModel):
    produto_id: uuid.UUID
    nome: str
    preco_base: Decimal
    categoria: str
    sazonal: bool


class DisponibilidadeIn(BaseModel):
    preco_local: Decimal | None = Field(default=None, ge=0)
    disponivel: bool = True
    quantidade_estoque: int | None = Field(default=None, ge=0)
    inicio_vigencia: date | None = None
    fim_vigencia: date | None = None


class UnidadeCreate(BaseModel):
    nome: str
    regiao: str
    cidade: str
    formato_operacao: FormatoOperacao = FormatoOperacao.COMPLETA
    ativa: bool = True


class UnidadeUpdate(BaseModel):
    nome: str | None = None
    regiao: str | None = None
    cidade: str | None = None
    formato_operacao: FormatoOperacao | None = None
    ativa: bool | None = None
