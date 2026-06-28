from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.catalog import AuditLog
from app.models.order import Pedido
from app.models.user import ResgatePontos, Usuario

FINALIDADE_FIDELIDADE = "FIDELIDADE"


def acumular_pontos(db: Session, pedido: Pedido) -> int:
    """credita 1 ponto por real ao dono do pedido, se tiver consentimento FIDELIDADE ativo"""
    if pedido.usuario_id is None:
        return 0
    usuario = db.get(Usuario, pedido.usuario_id)
    if usuario is None or not usuario.tem_consentimento(FINALIDADE_FIDELIDADE):
        return 0

    pontos = int(pedido.valor_total)
    if pontos <= 0:
        return 0
    usuario.pontos_fidelidade += pontos
    db.add(
        AuditLog(
            ator_id=usuario.id,
            pedido_id=pedido.id,
            acao="ACUMULAR_PONTOS",
            entidade="usuario",
            detalhes={"pontos": pontos, "saldo": usuario.pontos_fidelidade},
        )
    )
    return pontos


def resgatar_pontos(db: Session, usuario: Usuario, pontos: int) -> ResgatePontos:
    """debita pontos do saldo e gera um cupom. levanta ValueError se saldo insuficiente"""
    if usuario.pontos_fidelidade < pontos:
        raise ValueError("Saldo de pontos insuficiente.")

    usuario.pontos_fidelidade -= pontos
    cupom = f"RAIZ-{uuid.uuid4().hex[:8].upper()}"
    resgate = ResgatePontos(usuario_id=usuario.id, pontos=pontos, cupom=cupom)
    db.add(resgate)
    db.add(
        AuditLog(
            ator_id=usuario.id,
            acao="RESGATAR_PONTOS",
            entidade="resgate_pontos",
            detalhes={"pontos": pontos, "cupom": cupom, "saldo": usuario.pontos_fidelidade},
        )
    )
    db.flush()
    return resgate
