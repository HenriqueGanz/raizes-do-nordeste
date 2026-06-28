from __future__ import annotations

from app.payments.base import PaymentRequest, PaymentResult, PaymentStrategy
from app.payments.strategies import ESTRATEGIAS_DISPONIVEIS


class PaymentProcessor:

    def __init__(self, strategy: PaymentStrategy) -> None:
        self._strategy = strategy

    @property
    def provedor(self) -> str:
        return self._strategy.nome

    def processar(self, request: PaymentRequest) -> PaymentResult:
        return self._strategy.autorizar(request)

    def consultar(self, id_transacao_externa: str) -> PaymentResult:
        return self._strategy.consultar(id_transacao_externa)


def criar_payment_processor(nome_provedor: str) -> PaymentProcessor:
    strategy_cls = ESTRATEGIAS_DISPONIVEIS.get(nome_provedor.upper())
    if strategy_cls is None:
        raise ValueError(f"Provedor de pagamento não suportado: {nome_provedor}")
    return PaymentProcessor(strategy_cls())
