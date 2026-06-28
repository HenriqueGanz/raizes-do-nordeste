"""Importante frizar aqui que em prod, cada classe faria chamadas HTTP ao gateway real (com timeout, retry e
idempotency_key), aqui a integracaoo é apenas simulada.
"""
from __future__ import annotations

import uuid

from app.payments.base import (
    PaymentRequest,
    PaymentResult,
    PaymentStrategy,
    ResultadoPagamento,
)


class PixGatewayStrategy(PaymentStrategy):
    """provedor Pix simulado"""

    nome = "PIX"

    def autorizar(self, request: PaymentRequest) -> PaymentResult:
        # aceita instantaneamente
        tx = f"tx_pix_{uuid.uuid4().hex[:10]}"
        return PaymentResult(
            resultado=ResultadoPagamento.APROVADO,
            id_transacao_externa=tx,
            mensagem="Pagamento Pix autorizado (simulado).",
        )

    def consultar(self, id_transacao_externa: str) -> PaymentResult:
        return PaymentResult(
            resultado=ResultadoPagamento.APROVADO,
            id_transacao_externa=id_transacao_externa,
        )


class CreditCardGatewayStrategy(PaymentStrategy):
    """provedor de cartão simulado"""

    nome = "CARTAO_CREDITO"

    def autorizar(self, request: PaymentRequest) -> PaymentResult:
        tx = f"tx_cc_{uuid.uuid4().hex[:10]}"
        # cartão fica PENDENTE até ser confirmado via webhook.
        return PaymentResult(
            resultado=ResultadoPagamento.PENDENTE,
            id_transacao_externa=tx,
            mensagem="Autorização de cartão em processamento (simulado).",
        )

    def consultar(self, id_transacao_externa: str) -> PaymentResult:
        return PaymentResult(
            resultado=ResultadoPagamento.PENDENTE,
            id_transacao_externa=id_transacao_externa,
        )


# mapeia o nome do provedor a strategy usada pela factory
ESTRATEGIAS_DISPONIVEIS: dict[str, type[PaymentStrategy]] = {
    PixGatewayStrategy.nome: PixGatewayStrategy,
    CreditCardGatewayStrategy.nome: CreditCardGatewayStrategy,
}
