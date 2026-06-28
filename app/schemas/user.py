from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


def _normalizar_cpf(v: str | None) -> str | None:
    if v is None:
        return None
    digitos = re.sub(r"\D", "", v)
    if len(digitos) != 11:
        raise ValueError("CPF deve conter 11 dígitos.")
    return digitos


class ClienteCreate(BaseModel):
    nome: str
    email: str
    senha: str = Field(min_length=6)
    cpf: str | None = None
    data_nascimento: date | None = None

    _cpf = field_validator("cpf")(_normalizar_cpf)


class ClienteUpdate(BaseModel):
    nome: str | None = None
    email: str | None = None
    cpf: str | None = None
    data_nascimento: date | None = None

    _cpf = field_validator("cpf")(_normalizar_cpf)


class ClienteOut(BaseModel):
    cliente_id: uuid.UUID
    nome: str | None = None
    email: str | None = None
    cpf: str | None = None
    pontos_fidelidade: int
    papel: str


class ResgateIn(BaseModel):
    pontos: int = Field(gt=0)


class ResgateOut(BaseModel):
    resgate_id: uuid.UUID
    pontos: int
    cupom: str
    saldo_restante: int


class PedidoResumo(BaseModel):
    pedido_id: uuid.UUID
    status: str
    valor_total: Decimal
    canal: str
    criado_em: datetime | None = None
