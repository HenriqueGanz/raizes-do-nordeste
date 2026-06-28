from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


class ResultadoPagamento(str, enum.Enum):
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"
    PENDENTE = "PENDENTE"


@dataclass(frozen=True)
class PaymentRequest:
    pedido_id: str
    valor: Decimal
    metodo: str
    idempotency_key: str


@dataclass(frozen=True)
class PaymentResult:
    resultado: ResultadoPagamento
    id_transacao_externa: str | None = None
    mensagem: str | None = None


class PaymentStrategy(ABC):
    nome: str = "abstract"

    @abstractmethod
    def autorizar(self, request: PaymentRequest) -> PaymentResult:

    @abstractmethod
    def consultar(self, id_transacao_externa: str) -> PaymentResult:
