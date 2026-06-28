from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CanalPedido(str, enum.Enum):
    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"


class StatusPedido(str, enum.Enum):
    CRIADO = "CRIADO"
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    PAGO = "PAGO"
    PAGAMENTO_RECUSADO = "PAGAMENTO_RECUSADO"
    EM_PREPARO = "EM_PREPARO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


class StatusPagamento(str, enum.Enum):
    PENDENTE = "PENDENTE"
    PAGO = "PAGO"
    RECUSADO = "RECUSADO"
    ESTORNADO = "ESTORNADO"


# transicoes validas da maquina de estados do pedido.
TRANSICOES_VALIDAS: dict[StatusPedido, set[StatusPedido]] = {
    StatusPedido.CRIADO: {StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.CANCELADO},
    StatusPedido.AGUARDANDO_PAGAMENTO: {
        StatusPedido.PAGO, StatusPedido.PAGAMENTO_RECUSADO, StatusPedido.CANCELADO
    },
    StatusPedido.PAGAMENTO_RECUSADO: {StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.CANCELADO},
    StatusPedido.PAGO: {StatusPedido.EM_PREPARO, StatusPedido.CANCELADO},
    StatusPedido.EM_PREPARO: {StatusPedido.PRONTO},
    StatusPedido.PRONTO: {StatusPedido.ENTREGUE},
}


class Pedido(Base):
    __tablename__ = "pedido"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    unidade_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("usuario.id")
    )
    canal: Mapped[CanalPedido] = mapped_column(Enum(CanalPedido, name="canal_pedido"), nullable=False)
    status: Mapped[StatusPedido] = mapped_column(
        Enum(StatusPedido, name="status_pedido"), default=StatusPedido.CRIADO, nullable=False
    )
    valor_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    itens: Mapped[list["ItemPedido"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan"
    )
    pagamento: Mapped["Pagamento | None"] = relationship(
        back_populates="pedido", uselist=False, cascade="all, delete-orphan"
    )

    def calcular_total(self) -> Decimal:
        self.valor_total = sum((item.subtotal() for item in self.itens), Decimal("0"))
        return self.valor_total

    def transicionar_para(self, novo: StatusPedido) -> None:
        """so muda se for valido na maquina de estados."""
        permitidos = TRANSICOES_VALIDAS.get(self.status, set())
        if novo not in permitidos:
            raise ValueError(f"Transição inválida: {self.status.value} -> {novo.value}")
        self.status = novo


class ItemPedido(Base):
    __tablename__ = "item_pedido"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    pedido_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("pedido.id", ondelete="CASCADE"), nullable=False
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    pedido: Mapped["Pedido"] = relationship(back_populates="itens")

    def subtotal(self) -> Decimal:
        return Decimal(self.preco_unitario) * self.quantidade


class Pagamento(Base):
    __tablename__ = "pagamento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    pedido_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("pedido.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    metodo: Mapped[str] = mapped_column(String(30), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[StatusPagamento] = mapped_column(
        Enum(StatusPagamento, name="status_pagamento"), default=StatusPagamento.PENDENTE, nullable=False
    )
    id_transacao_externa: Mapped[str | None] = mapped_column(String(100))
    # Garante idempotencia no processamento do webhook do gateway externo.
    idempotency_key: Mapped[str | None] = mapped_column(String(120), unique=True)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    pedido: Mapped["Pedido"] = relationship(back_populates="pagamento")
