from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FormatoOperacao(str, enum.Enum):
    COMPLETA = "COMPLETA"
    REDUZIDA = "REDUZIDA"


class Unidade(Base):
    __tablename__ = "unidade"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    regiao: Mapped[str] = mapped_column(String(60), nullable=False)
    cidade: Mapped[str] = mapped_column(String(80), nullable=False)
    formato_operacao: Mapped[FormatoOperacao] = mapped_column(
        Enum(FormatoOperacao, name="formato_operacao"),
        default=FormatoOperacao.COMPLETA,
        nullable=False,
    )
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Produto(Base):
    __tablename__ = "produto"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    preco_base: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    categoria: Mapped[str] = mapped_column(String(60), nullable=False)
    sazonal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DisponibilidadeProduto(Base):
    __tablename__ = "disponibilidade_produto"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    unidade_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("unidade.id", ondelete="CASCADE"), nullable=False
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("produto.id", ondelete="CASCADE"), nullable=False
    )
    preco_local: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    disponivel: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # o estoque local é gerido pela propria unidade
    quantidade_estoque: Mapped[int | None] = mapped_column(Integer)
    inicio_vigencia: Mapped[date | None] = mapped_column(Date)
    fim_vigencia: Mapped[date | None] = mapped_column(Date)

    produto: Mapped["Produto"] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ator_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    pedido_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("pedido.id", ondelete="SET NULL")
    )
    acao: Mapped[str] = mapped_column(String(60), nullable=False)
    entidade: Mapped[str] = mapped_column(String(60), nullable=False)
    detalhes: Mapped[dict | None] = mapped_column(JSON)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
