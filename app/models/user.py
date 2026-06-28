from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StatusConsentimento(str, enum.Enum):
    CONCEDIDO = "CONCEDIDO"
    REVOGADO = "REVOGADO"


class PapelUsuario(str, enum.Enum):
    CLIENTE = "CLIENTE"
    OPERADOR = "OPERADOR"
    ADMIN = "ADMIN"


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nome: Mapped[str | None] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(180), unique=True)
    cpf: Mapped[str | None] = mapped_column(String(11), unique=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date)
    pontos_fidelidade: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    papel: Mapped[PapelUsuario] = mapped_column(
        Enum(PapelUsuario, name="papel_usuario"), default=PapelUsuario.CLIENTE, nullable=False
    )
    # nulo para clientes criados atraves do CPF no totem, sem login
    senha_hash: Mapped[str | None] = mapped_column(String(200))

    # LGPD
    anonimizado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    consentimentos: Mapped[list["Consentimento"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )

    def tem_consentimento(self, finalidade: str) -> bool:
        return any(
            c.finalidade == finalidade and c.status == StatusConsentimento.CONCEDIDO
            for c in self.consentimentos
        )

    def anonimizar(self) -> None:
        self.nome = None
        self.email = None
        self.cpf = None
        self.data_nascimento = None
        self.senha_hash = None
        self.anonimizado = True
        self.anonymized_at = datetime.now(UTC)


class ResgatePontos(Base):
    __tablename__ = "resgate_pontos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False
    )
    pontos: Mapped[int] = mapped_column(Integer, nullable=False)
    cupom: Mapped[str] = mapped_column(String(40), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Consentimento(Base):
    __tablename__ = "consentimento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False
    )
    finalidade: Mapped[str] = mapped_column(String(80), nullable=False)
    base_legal: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[StatusConsentimento] = mapped_column(
        Enum(StatusConsentimento, name="status_consentimento"),
        default=StatusConsentimento.CONCEDIDO,
        nullable=False,
    )
    versao_termo: Mapped[str | None] = mapped_column(String(20))
    concedido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    usuario: Mapped["Usuario"] = relationship(back_populates="consentimentos")

    def revogar(self) -> None:
        self.status = StatusConsentimento.REVOGADO
        self.revogado_em = datetime.now(UTC)
