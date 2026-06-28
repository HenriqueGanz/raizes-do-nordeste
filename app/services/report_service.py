from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import Unidade
from app.models.order import Pedido, StatusPedido

# pedidos que contam como venda
VENDAS_STATUS = (
    StatusPedido.PAGO,
    StatusPedido.EM_PREPARO,
    StatusPedido.PRONTO,
    StatusPedido.ENTREGUE,
)


def vendas_por_unidade(
    db: Session,
    unidade_id: uuid.UUID | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> list[dict]:
    stmt = (
        select(
            Unidade.id,
            Unidade.nome,
            func.count(Pedido.id),
            func.coalesce(func.sum(Pedido.valor_total), 0),
            func.coalesce(func.avg(Pedido.valor_total), 0),
        )
        .join(Pedido, Pedido.unidade_id == Unidade.id)
        .where(Pedido.status.in_(VENDAS_STATUS))
        .group_by(Unidade.id, Unidade.nome)
        .order_by(Unidade.nome)
    )
    if unidade_id is not None:
        stmt = stmt.where(Unidade.id == unidade_id)
    if data_inicio is not None:
        stmt = stmt.where(Pedido.criado_em >= datetime.combine(data_inicio, time.min))
    if data_fim is not None:
        stmt = stmt.where(Pedido.criado_em <= datetime.combine(data_fim, time.max))

    linhas = []
    for uid, nome, total, faturamento, ticket in db.execute(stmt).all():
        linhas.append(
            {
                "unidade_id": str(uid),
                "unidade": nome,
                "total_pedidos": int(total),
                "faturamento": round(float(faturamento), 2),
                "ticket_medio": round(float(ticket), 2),
            }
        )
    return linhas
