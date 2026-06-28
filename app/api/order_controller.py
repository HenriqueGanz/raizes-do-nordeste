from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_opcional, get_payment_processor
from app.core.database import get_db
from app.models.order import (
    CanalPedido,
    ItemPedido,
    Pagamento,
    Pedido,
    StatusPagamento,
    StatusPedido,
)
from app.models.user import Usuario
from app.payments.base import PaymentRequest
from app.payments.processor import PaymentProcessor
from app.schemas.order import ItemPedidoOut, PagamentoOut, PedidoCreate, PedidoOut
from app.services import catalog_service, user_service

router = APIRouter(prefix="/v1", tags=["pedidos"])


@router.post("/pedidos", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def criar_pedido(
    payload: PedidoCreate,
    db: Session = Depends(get_db),
    payment: PaymentProcessor = Depends(get_payment_processor),
    usuario_autenticado: Usuario | None = Depends(get_current_user_opcional),
) -> PedidoOut:
    """Cria um pedido com os produtos e quantidades escolhidos. Antes de testar, pega o
    `unidade_id` em `/unidades` e os `produto_id` no cardápio daquela unidade.

    No canal `APP`, precisa estar logado (usa o cadeado do Swagger com o token de algum CLIENTE),
    o pedido fica vinculado automaticamente a quem está logado, sem precisar mandar nenhum
    dado de cliente no corpo. Nos canais `TOTEM`, `BALCAO` e `PICKUP` não precisa de login, mas
    dá pra mandar o CPF do cliente demo (12345678900) pra ele ganhar pontos de fidelidade quando
    o pagamento for confirmado.
    """
    unidade = catalog_service.obter_unidade(db, payload.unidade_id)
    if unidade is None:
        raise HTTPException(status_code=404, detail="Unidade não encontrada ou inativa.")

    if payload.canal == CanalPedido.APP:
        if usuario_autenticado is None:
            raise HTTPException(status_code=401, detail="Pedido pelo app exige cliente autenticado.")
        if payload.cpf:
            raise HTTPException(
                status_code=422,
                detail="cpf não se aplica ao canal APP; o cliente já é identificado pelo login.",
            )
        usuario_id = usuario_autenticado.id
    else:
        # no totem, balcao ou pick-up o cliente pode ser anonimo
        # ou cria o cadastro para pontos e historico.
        usuario_id = user_service.find_or_create_por_cpf(db, payload.cpf).id if payload.cpf else None

    hoje = date.today()
    pedido = Pedido(
        unidade_id=payload.unidade_id,
        usuario_id=usuario_id,
        canal=payload.canal,
        status=StatusPedido.CRIADO,
    )

    for item_in in payload.itens:
        preco = catalog_service.preco_disponivel(db, payload.unidade_id, item_in.produto_id, hoje)
        if preco is None:
            raise HTTPException(
                status_code=422,
                detail=f"Produto {item_in.produto_id} indisponível nesta unidade.",
            )
        pedido.itens.append(
            ItemPedido(
                produto_id=item_in.produto_id,
                quantidade=item_in.quantidade,
                preco_unitario=preco,
            )
        )
        catalog_service.baixar_estoque(db, payload.unidade_id, item_in.produto_id, item_in.quantidade)

    pedido.calcular_total()
    pedido.transicionar_para(StatusPedido.AGUARDANDO_PAGAMENTO)

    # persistencia do pedido
    idem_key = f"pay_{uuid.uuid4().hex}"
    pagamento = Pagamento(
        metodo=payload.metodo_pagamento,
        valor=pedido.valor_total,
        status=StatusPagamento.PENDENTE,
        idempotency_key=idem_key,
    )
    pedido.pagamento = pagamento

    # Solicita a autorização ao gateway via Strategy
    # retornamos só o protocolo da solicitação, quem confirma o pagamento
    # é o webhook de maneira assíncrona
    resultado = payment.processar(
        PaymentRequest(
            pedido_id=str(pedido.id),
            valor=pedido.valor_total,
            metodo=payload.metodo_pagamento,
            idempotency_key=idem_key,
        )
    )
    pagamento.id_transacao_externa = resultado.id_transacao_externa

    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    return _to_out(pedido)


@router.get("/pedidos/{pedido_id}", response_model=PedidoOut)
def obter_pedido(pedido_id: uuid.UUID, db: Session = Depends(get_db)) -> PedidoOut:
    """Consulta como está o pedido (status, itens e pagamento). Usa o `pedido_id` que veio na
    resposta de quando você criou o pedido em `POST /pedidos`.
    """
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    return _to_out(pedido)


def _to_out(pedido: Pedido) -> PedidoOut:
    return PedidoOut(
        pedido_id=pedido.id,
        status=pedido.status,
        valor_total=pedido.valor_total,
        canal=pedido.canal,
        itens=[
            ItemPedidoOut(
                produto_id=i.produto_id,
                quantidade=i.quantidade,
                subtotal=i.subtotal(),
            )
            for i in pedido.itens
        ],
        pagamento=(
            PagamentoOut(
                metodo=pedido.pagamento.metodo,
                status=pedido.pagamento.status.value,
                idempotency_key=pedido.pagamento.idempotency_key,
                id_transacao_externa=pedido.pagamento.id_transacao_externa,
            )
            if pedido.pagamento
            else None
        ),
    )
