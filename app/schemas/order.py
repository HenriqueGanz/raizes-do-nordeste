from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.order import CanalPedido, StatusPedido
from app.schemas.user import _normalizar_cpf


class ItemPedidoIn(BaseModel):
    produto_id: uuid.UUID
    quantidade: int = Field(gt=0)


class PedidoCreate(BaseModel):
    unidade_id: uuid.UUID
    # CPF opcional totem, balcão, pick-up - vincula/cria o cliente para pontos e historico
    # no APP a identidade vem do login
    cpf: str | None = None
    canal: CanalPedido
    metodo_pagamento: str = "PIX"
    itens: list[ItemPedidoIn] = Field(min_length=1)

    _cpf = field_validator("cpf")(_normalizar_cpf)


class DescontoIn(BaseModel):
    percentual: Decimal | None = Field(default=None, ge=0, le=100)
    valor: Decimal | None = Field(default=None, ge=0)
    motivo: str | None = None


class PagamentoOut(BaseModel):
    metodo: str
    status: str
    idempotency_key: str | None = None
    id_transacao_externa: str | None = None


class ItemPedidoOut(BaseModel):
    produto_id: uuid.UUID
    quantidade: int
    subtotal: Decimal


class PedidoOut(BaseModel):
    pedido_id: uuid.UUID
    status: StatusPedido
    valor_total: Decimal
    canal: CanalPedido
    itens: list[ItemPedidoOut] = []
    pagamento: PagamentoOut | None = None
