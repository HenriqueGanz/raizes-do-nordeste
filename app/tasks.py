"""Aqui temos as tarefas assíncronas (Celery)
Processamento de pagamentos fora do ciclo de request HTTP, em prod
o OrderController publicaria esta tarefa (`solicitar_pagamento.delay(...)`) em vez de
chamar o gateway de forma síncrona, garantindo tolerância a falhas via retry/DLQ.
"""
from __future__ import annotations

from decimal import Decimal

from app.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.order import Pagamento, Pedido, StatusPagamento, StatusPedido
from app.payments.base import PaymentRequest, ResultadoPagamento
from app.payments.processor import criar_payment_processor


@celery_app.task(bind=True, max_retries=5, default_retry_delay=5)
def solicitar_pagamento(self, pedido_id: str) -> str:
    """solicita o pagamento ao gateway e registra o resultado.

    Se falhar, o Celery executa novamente com backoff, se esgotar as
    tentativas, a mensagem segue para a DLQ configurada
    """
    db = SessionLocal()
    try:
        pedido = db.get(Pedido, pedido_id)
        if pedido is None or pedido.pagamento is None:
            return "pedido_inexistente"

        pagamento: Pagamento = pedido.pagamento
        processor = criar_payment_processor(settings.payment_gateway)
        try:
            resultado = processor.processar(
                PaymentRequest(
                    pedido_id=str(pedido.id),
                    valor=Decimal(pagamento.valor),
                    metodo=pagamento.metodo,
                    idempotency_key=pagamento.idempotency_key or str(pedido.id),
                )
            )
        except Exception as exc:
            raise self.retry(exc=exc)

        if resultado.resultado is ResultadoPagamento.APROVADO:
            pagamento.status = StatusPagamento.PAGO
            pagamento.id_transacao_externa = resultado.id_transacao_externa
            pedido.transicionar_para(StatusPedido.PAGO)
        else:
            pagamento.id_transacao_externa = resultado.id_transacao_externa
        db.commit()
        return resultado.resultado.value
    finally:
        db.close()
